"""Gateway fictício para demonstração local do webhook."""
from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Gateway antifraude fictício")


class WebhookPayload(BaseModel):
    transfer_id: int
    source_id: int
    destination_id: int
    amount: Decimal


@app.post("/webhook", status_code=202)
def receive_transfer(payload: WebhookPayload):
    return {"received": payload.transfer_id}
