from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import Mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from src.domain.models import Account, LedgerEntry, Transfer
from src.domain.rules import DomainError
from src.repositories.database import init_db, make_engine
from src.services.wallet import create_account, transfer_funds


@pytest.mark.parametrize("reuse_key", [False, True])
def test_concurrent_transfers_preserve_balance(tmp_path, reuse_key):
    engine = make_engine(f"sqlite:///{tmp_path / 'concurrent.db'}")
    init_db(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    notifier = Mock()
    barrier = Barrier(2)
    with sessions() as db:
        source = create_account(db, "Origem", Decimal("10")).id
        target = create_account(db, "Destino", Decimal("0")).id

    def attempt(number):
        with sessions() as db:
            barrier.wait(timeout=5)
            try:
                transfer, created = transfer_funds(
                    db, source, target, Decimal("10"), str(0 if reuse_key else number), notifier
                )
            except DomainError as error:
                assert str(error) == "Saldo insuficiente"
                return None, "insufficient"
            return transfer.id, "created" if created else "replayed"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, range(2)))
        expected = "replayed" if reuse_key else "insufficient"
        assert sorted(status for _, status in results) == ["created", expected]
        if reuse_key:
            assert results[0][0] == results[1][0]
        with sessions() as db:
            assert db.get(Account, source).balance == 0
            assert db.get(Account, target).balance == 10
            assert len(db.scalars(select(Transfer)).all()) == 1
            assert len(db.scalars(select(LedgerEntry)).all()) == 2
        notifier.notify.assert_called_once()
    finally:
        engine.dispose()
