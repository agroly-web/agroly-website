from django import forms

from agroly.akuntansi.form_helpers import siapkan_field_akun

from .models import BarangPersediaan, MutasiPersediaan


class BarangPersediaanForm(forms.ModelForm):
    class Meta:
        model = BarangPersediaan
        fields = ["kode_barang", "nama_barang", "stok", "satuan", "harga_beli", "harga_jual", "aktif"]


class MutasiPersediaanForm(forms.ModelForm):
    class Meta:
        model = MutasiPersediaan
        fields = [
            "nomor_dokumen",
            "tanggal",
            "barang",
            "tipe_mutasi",
            "jumlah",
            "harga_per_unit",
            "akun",
            "saldo_setelah",
            "keterangan",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        siapkan_field_akun(self.fields["akun"])
        self.fields["barang"].empty_label = "Pilih barang"
