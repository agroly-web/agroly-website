"""Helper untuk field form terkait akun."""

from django import forms

from .models import Akun


def label_akun_dropdown(akun: Akun) -> str:
    return f"{akun.kode_akun} — {akun.nama_akun}"


def siapkan_field_akun(
    field: forms.ModelChoiceField,
    *,
    queryset=None,
    empty_label: str = "Pilih akun",
) -> None:
    if queryset is None:
        queryset = Akun.objects.filter(aktif=True).order_by("kode_akun")
    field.queryset = queryset
    field.label_from_instance = label_akun_dropdown
    field.empty_label = empty_label
