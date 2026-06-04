from decimal import Decimal, ROUND_HALF_UP


def format_rupiah(nilai) -> str:
    """Format formal: Rp. 5.000.000"""
    amount = Decimal(nilai or 0).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    integer_text = f"{int(amount):,}".replace(",", ".")
    return f"{sign}Rp. {integer_text}"


def format_rupiah_neraca(nilai) -> str:
    """Nilai negatif neraca dalam tanda kurung."""
    amount = Decimal(nilai or 0).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if amount < 0:
        return f"({format_rupiah(abs(amount))})"
    return format_rupiah(amount)
