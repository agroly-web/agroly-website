from decimal import Decimal

from django import template

from agroly.utils.format_rupiah import format_rupiah, format_rupiah_neraca

register = template.Library()


@register.filter
def format_rp(nilai):
    return format_rupiah(nilai)


@register.filter
def format_rp_neraca(nilai):
    return format_rupiah_neraca(nilai)


@register.filter
def format_rp_kosong(nilai):
    amount = Decimal(nilai or 0)
    if amount == 0:
        return ""
    return format_rupiah(amount)
