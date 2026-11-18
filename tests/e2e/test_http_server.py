"""Fluxo completo por TCP/HTTP, com Uvicorn e banco exclusivo do teste."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from decimal import Decimal

import httpx
import pytest


@pytest.fixture
def live_api(tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'http.db').as_posix()}"
    env.pop("ANTIFRAUD_WEBHOOK_URL", None)
    root = Path(__file__).resolve().parents[2]
    with (tmp_path / "uvicorn.log").open("w+", encoding="utf-8") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False) as client:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline and server.poll() is None:
                    try:
                        if client.get("/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.1)
                else:
                    log.seek(0)
                    pytest.fail(f"Uvicorn não iniciou: {log.read()}")
                yield client
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


def test_account_transfer_and_statement_over_real_http(live_api):
    source = live_api.post("/accounts", json={"owner": "Ana HTTP", "initial_balance": "100.00"})
    target = live_api.post("/accounts", json={"owner": "Bia HTTP", "initial_balance": "0.00"})
    assert source.status_code == target.status_code == 201
    source_id, target_id = source.json()["id"], target.json()["id"]
    payload = {"source_id": source_id, "destination_id": target_id,
               "amount": "25.00", "idempotency_key": "http-e2e"}
    transfer = live_api.post("/transfers", json=payload)
    assert transfer.status_code == 201
    assert transfer.json()["created"] is True
    replay = live_api.post("/transfers", json=payload)
    assert replay.is_success
    assert replay.json()["id"] == transfer.json()["id"]
    assert replay.json()["created"] is False
    for account_id, balance, kind in [(source_id, "75.00", "debit"), (target_id, "25.00", "credit")]:
        account = live_api.get(f"/accounts/{account_id}")
        assert account.status_code == 200
        assert Decimal(str(account.json()["balance"])) == Decimal(balance)
        statement = live_api.get(f"/accounts/{account_id}/statement", params={"kind": kind})
        assert statement.status_code == 200
        entry, = statement.json()
        assert entry["kind"] == kind
        assert Decimal(str(entry["amount"])) == Decimal("25.00")
        filtered = live_api.get(f"/accounts/{account_id}/statement", params={
            "kind": kind, "start": entry["created_at"], "end": entry["created_at"],
        })
        assert filtered.status_code == 200
        assert filtered.json() == [entry]
    failed = live_api.post("/transfers", json={**payload, "amount": "1000.00", "idempotency_key": "http-no-funds"})
    assert failed.status_code == 400
    assert Decimal(str(live_api.get(f"/accounts/{source_id}").json()["balance"])) == Decimal("75.00")
    assert len(live_api.get(f"/accounts/{source_id}/statement").json()) == 1
