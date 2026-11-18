from decimal import Decimal

def test_full_flow(client):
    a = client.post("/accounts", json={"owner": "Ana", "initial_balance": "100.00"})
    b = client.post("/accounts", json={"owner": "Bia", "initial_balance": "0"})
    assert a.status_code == b.status_code == 201
    aid, bid = a.json()["id"], b.json()["id"]
    payload = {"source_id": aid, "destination_id": bid, "amount": "25", "idempotency_key": "abc"}
    assert client.post("/transfers", json=payload).status_code == 201
    assert client.post("/transfers", json=payload).json()["created"] is False
    assert float(client.get(f"/accounts/{aid}").json()["balance"]) == 75
    assert float(client.get(f"/accounts/{bid}").json()["balance"]) == 25
    debit = client.get(f"/accounts/{aid}/statement", params={"kind": "debit"})
    credit = client.get(f"/accounts/{bid}/statement", params={"kind": "credit"})
    assert debit.status_code == credit.status_code == 200
    assert len(debit.json()) == len(credit.json()) == 1
    assert client.get(f"/accounts/{aid}/statement", params={"start": "2020-01-01T00:00:00", "end": "2030-01-01T00:00:00"}).status_code == 200


def test_api_errors(client):
    assert client.get("/accounts/999").status_code == 404
    assert client.get("/accounts/999/statement").status_code == 404
    assert client.post("/accounts", json={"owner": " ", "initial_balance": 0}).status_code == 400
    a = client.post("/accounts", json={"owner": "Ana", "initial_balance": 5}).json()["id"]
    b = client.post("/accounts", json={"owner": "Bia", "initial_balance": 0}).json()["id"]
    assert client.post("/transfers", json={"source_id": a, "destination_id": b, "amount": 100, "idempotency_key": "no"}).status_code == 400
    assert client.get(f"/accounts/{a}/statement", params={"kind": "other"}).status_code == 422
    assert client.get(f"/accounts/{a}/statement", params={"start": "2030-01-01T00:00:00", "end": "2020-01-01T00:00:00"}).status_code == 400


def test_statement_accepts_mixed_timestamp_offsets(client):
    account = client.post("/accounts", json={"owner": "Ana"}).json()["id"]
    response = client.get(f"/accounts/{account}/statement", params={
        "start": "2020-01-01T00:00:00",
        "end": "2030-01-01T00:00:00-03:00",
    })
    assert response.status_code == 200
    assert response.json() == []


def test_statement_date_filter_excludes_outside_interval(client):
    assert client.get("/health").json() == {"status": "ok"}
    source = client.post("/accounts", json={"owner": "Ana", "initial_balance": "2.00"}).json()["id"]
    target = client.post("/accounts", json={"owner": "Bia"}).json()["id"]
    response = client.post("/transfers", json={
        "source_id": source, "destination_id": target, "amount": "1.00", "idempotency_key": "filter",
    })
    assert response.status_code == 201
    path = f"/accounts/{source}/statement"
    assert client.get(path, params={"end": "2000-01-01T00:00:00Z"}).json() == []
    assert client.get(path, params={"kind": "credit"}).json() == []
    entry, = client.get(path).json()
    assert entry["kind"] == "debit"
    assert Decimal(str(entry["amount"])) == Decimal("1.00")
    assert entry["created_at"].endswith(("+00:00", "Z"))
    assert client.get(path, params={"start": entry["created_at"], "end": entry["created_at"]}).json() == [entry]
