import os

import httpx

from src.domain.models import Transfer


class Notifier:
    def notify(self, transfer: Transfer) -> None:
        url = os.getenv("ANTIFRAUD_WEBHOOK_URL")
        if url:
            response = httpx.post(url, json={
                "transfer_id": transfer.id,
                "source_id": transfer.source_id,
                "destination_id": transfer.destination_id,
                "amount": str(transfer.amount),
            }, timeout=2.0, trust_env=False)
            response.raise_for_status()
