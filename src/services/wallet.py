import logging
from decimal import Decimal

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from src.domain.models import Account, Transfer, LedgerEntry
from src.domain.rules import MAX_BALANCE, DomainError, valid_money, validate_amount
from src.services.antifraud import Notifier


logger = logging.getLogger(__name__)


class RegistrationStub:
    def is_valid(self, owner: str) -> bool:
        return bool(owner.strip())


def create_account(db: Session, owner: str, initial_balance: Decimal, validator=None):
    validator = validator or RegistrationStub()
    if not validator.is_valid(owner):
        raise DomainError("Cadastro inválido")
    if not valid_money(initial_balance) or not 0 <= initial_balance <= MAX_BALANCE:
        raise DomainError("Saldo inicial inválido")
    account = Account(owner=owner, balance=initial_balance)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def transfer_funds(db: Session, source_id: int, destination_id: int, amount: Decimal, key: str, notifier=None):
    validate_amount(amount)
    if source_id == destination_id:
        raise DomainError("Contas devem ser diferentes")
    if not key.strip():
        raise DomainError("Chave de idempotência obrigatória")
    existing = db.scalar(select(Transfer).where(Transfer.idempotency_key == key))
    if existing:
        if (existing.source_id, existing.destination_id, existing.amount) != (source_id, destination_id, amount):
            raise DomainError("Chave de idempotência reutilizada com outros dados")
        return existing, False
    try:
        # UPDATE condicional é atômico: duas transferências não podem gastar o mesmo saldo.
        result = db.execute(update(Account).where(Account.id == source_id, Account.balance >= amount).values(balance=func.round(Account.balance - amount, 2)))
        if result.rowcount != 1:
            if not db.get(Account, source_id):
                raise DomainError("Conta de origem inexistente")
            raise DomainError("Saldo insuficiente")
        result = db.execute(
            update(Account)
            .where(Account.id == destination_id, Account.balance <= MAX_BALANCE - amount)
            .values(balance=func.round(Account.balance + amount, 2))
        )
        if result.rowcount != 1:
            if not db.get(Account, destination_id):
                raise DomainError("Conta de destino inexistente")
            raise DomainError("Saldo de destino acima do limite monetário")
        item = Transfer(source_id=source_id, destination_id=destination_id, amount=amount, idempotency_key=key)
        db.add(item)
        db.flush()
        db.add_all([
            LedgerEntry(account_id=source_id, transfer_id=item.id, kind="debit", amount=amount),
            LedgerEntry(account_id=destination_id, transfer_id=item.id, kind="credit", amount=amount),
        ])
        db.commit()
        db.refresh(item)
    except (DomainError, IntegrityError, OperationalError):
        db.rollback()
        # Em disputa pela mesma chave, a transação vencedora pode já ter concluído.
        winner = db.scalar(select(Transfer).where(Transfer.idempotency_key == key))
        if winner:
            if (winner.source_id, winner.destination_id, winner.amount) != (source_id, destination_id, amount):
                raise DomainError("Chave de idempotência reutilizada com outros dados")
            return winner, False
        raise
    try:
        (notifier or Notifier()).notify(item)
    except httpx.HTTPError:
        logger.warning("Falha no webhook antifraude da transferência %s", item.id)
    return item, True
