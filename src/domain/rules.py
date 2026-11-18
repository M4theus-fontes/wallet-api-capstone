from decimal import Decimal


MAX_BALANCE = Decimal("9999999999.99")


class DomainError(ValueError):
    pass


def validate_amount(amount: Decimal) -> Decimal:
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
        raise DomainError("O valor deve ser positivo e ter no máximo duas casas decimais")
    if amount > MAX_BALANCE:
        raise DomainError("Valor acima do limite monetário")
    return amount


def debit(balance: Decimal, amount: Decimal) -> Decimal:
    validate_amount(amount)
    if balance < amount:
        raise DomainError("Saldo insuficiente")
    return balance - amount
