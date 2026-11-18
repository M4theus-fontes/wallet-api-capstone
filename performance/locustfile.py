"""Carga sobre um par compartilhado, com primeira onda sincronizada."""
import csv
import os
import uuid

import requests
from gevent.event import Event
from locust import HttpUser, between, events, task
from locust.stats import PERCENTILES_TO_REPORT, StatsCSV

BURST_SIZE = int(os.getenv("WALLET_BURST_SIZE", "50"))


@events.test_start.add_listener
def prepare_accounts(environment, **_kwargs):
    environment.transfer_gate = Event()
    environment.transfer_ready = 0
    environment.account_ids = []
    for owner, balance in [("Origem da carga", "1000000"), ("Destino da carga", "0")]:
        response = requests.post(
            f"{environment.host}/accounts",
            json={"owner": owner, "initial_balance": balance},
            timeout=10,
        )
        response.raise_for_status()
        environment.account_ids.append(response.json()["id"])
    print(f"Contas da carga: {environment.account_ids}", flush=True)


@events.quitting.add_listener
def export_final_stats(environment, **_kwargs):
    prefix = getattr(environment.parsed_options, "csv_prefix", None)
    if prefix:
        with open(f"{prefix}_final.csv", "w", encoding="utf-8", newline="") as output:
            StatsCSV(environment, PERCENTILES_TO_REPORT).requests_csv(csv.writer(output))


class WalletUser(HttpUser):
    wait_time = between(0.05, 0.15)

    def on_start(self):
        self.environment.transfer_ready += 1
        if self.environment.transfer_ready == BURST_SIZE:
            print(f"Disparando a primeira onda com {BURST_SIZE} usuários", flush=True)
            self.environment.transfer_gate.set()
        if not self.environment.transfer_gate.wait(timeout=15):
            raise RuntimeError("Usuários insuficientes para a primeira onda de transferências")

    @task
    def transfer(self):
        source, destination = self.environment.account_ids
        with self.client.post("/transfers", json={
            "source_id": source,
            "destination_id": destination,
            "amount": "1.00",
            "idempotency_key": str(uuid.uuid4()),
        }, name="POST /transfers", timeout=10, catch_response=True) as response:
            if response.status_code == 201 and response.json().get("created") is not True:
                response.failure("Transferência inédita não foi registrada")
