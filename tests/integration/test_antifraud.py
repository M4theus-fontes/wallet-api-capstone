from decimal import Decimal
from unittest.mock import Mock

import httpx
import pytest

from src.services.wallet import create_account, transfer_funds


@pytest.mark.parametrize("status", [200, 503])
def test_webhook_payload_and_failure_isolation(db, monkeypatch, status, caplog):
    url = "https://antifraude.example.invalid/transfer"
    monkeypatch.setenv("ANTIFRAUD_WEBHOOK_URL", url)
    mocked_post = Mock(return_value=httpx.Response(status, request=httpx.Request("POST", url)))
    monkeypatch.setattr(httpx, "post", mocked_post)
    source = create_account(db, "Ana", Decimal("10"))
    target = create_account(db, "Bia", Decimal("0"))
    transfer, created = transfer_funds(db, source.id, target.id, Decimal("1"), "notify")
    assert created
    transfer_funds(db, source.id, target.id, Decimal("1"), "notify")
    mocked_post.assert_called_once_with(url, json={
        "transfer_id": transfer.id,
        "source_id": source.id,
        "destination_id": target.id,
        "amount": "1.00",
    }, timeout=2.0, trust_env=False)
    assert (source.balance, target.balance) == (9, 1)
    assert ("Falha no webhook" in caplog.text) == (status == 503)
