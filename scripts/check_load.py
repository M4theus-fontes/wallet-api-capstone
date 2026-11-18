"""Compara a medição do Locust aos saldos e lançamentos gravados."""
import argparse
import csv
from decimal import Decimal

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stats")
    parser.add_argument("origin", type=int)
    parser.add_argument("destination", type=int)
    parser.add_argument("--host", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    with open(args.stats, encoding="utf-8", newline="") as stats:
        row = next(row for row in csv.DictReader(stats) if row["Name"] == "POST /transfers")
    total = int(row["Request Count"])
    failures = int(row["Failure Count"])
    with httpx.Client(base_url=args.host, timeout=15, trust_env=False) as client:
        def read(path):
            return client.get(path).raise_for_status().json()

        origin = Decimal(str(read(f"/accounts/{args.origin}")["balance"]))
        destination = Decimal(str(read(f"/accounts/{args.destination}")["balance"]))
        debit = read(f"/accounts/{args.origin}/statement?kind=debit")
        credit = read(f"/accounts/{args.destination}/statement?kind=credit")

    print(f"Transferências HTTP: {total}; falhas: {failures}")
    print(f"Saldo origem: {origin}; saldo destino: {destination}")
    print(f"Débitos: {len(debit)}; créditos: {len(credit)}")
    verified = (
        total > 0 and failures == 0
        and origin == 1_000_000 - total and destination == total
        and len(debit) == len(credit) == total
    )
    print("Conciliação confirmada." if verified else "Divergência na conciliação.")
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
