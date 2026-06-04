from django import forms

from .models import ProduksiPanen


class ProduksiPanenForm(forms.ModelForm):
    class Meta:
        model = ProduksiPanen
        fields = ["tanggal", "komoditas", "grade", "jumlah_hasil_panen", "satuan", "keterangan"]
