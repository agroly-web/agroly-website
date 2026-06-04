from django import forms

from agroly.akuntansi.form_helpers import siapkan_field_akun
from agroly.akuntansi.models import Akun
from agroly.persediaan.models import BarangPersediaan

from .models import PembayaranUtang, PembelianBarang


class PembelianBarangForm(forms.ModelForm):
    barang = forms.ModelChoiceField(
        queryset=BarangPersediaan.objects.filter(aktif=True),
        label="Kode Barang",
    )
    jumlah = forms.DecimalField(max_digits=18, decimal_places=2, label="Kuantitas")
    harga_satuan = forms.DecimalField(max_digits=18, decimal_places=2, label="Harga")

    class Meta:
        model = PembelianBarang
        fields = [
            "tanggal",
            "supplier",
            "nomor_invoice",
            "nomor_faktur_pemasok",
            "termin_pembayaran",
            "diskon_persen",
            "pajak_persen",
            "status_pembayaran",
            "keterangan",
        ]
        widgets = {
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "termin_pembayaran": forms.TextInput(
                attrs={"placeholder": "2/10 n/30", "class": "form-control"}
            ),
            "nomor_invoice": forms.TextInput(attrs={"class": "form-control"}),
            "nomor_faktur_pemasok": forms.TextInput(attrs={"class": "form-control"}),
            "tanggal": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "diskon_persen": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "pajak_persen": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "status_pembayaran": forms.Select(attrs={"class": "form-select"}),
            "keterangan": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Keterangan (opsional)",
                    "maxlength": "255",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["barang"].label_from_instance = lambda obj: obj.kode_barang
        self.fields["barang"].widget.attrs["class"] = "form-select"
        self.fields["barang"].empty_label = "Pilih barang"
        self.fields["keterangan"].label = ""
        self.fields["keterangan"].required = False
        self.fields["supplier"].empty_label = "Pilih pemasok"


class PembayaranUtangForm(forms.ModelForm):
    class Meta:
        model = PembayaranUtang
        fields = [
            "tanggal",
            "akun_kas_bayar",
            "supplier",
            "no_cek",
            "nomor_bukti",
            "jumlah_bayar",
            "diskon",
            "keterangan",
        ]
        widgets = {
            "akun_kas_bayar": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "supplier": forms.Select(attrs={"class": "form-select form-select-sm", "id": "id_supplier"}),
            "no_cek": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "tanggal": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
            "nomor_bukti": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "jumlah_bayar": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01"}),
            "diskon": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01"}),
            "keterangan": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        siapkan_field_akun(
            self.fields["akun_kas_bayar"],
            queryset=Akun.objects.filter(kode_akun__startswith="111", aktif=True).order_by(
                "kode_akun"
            ),
            empty_label="Pilih rekening kas",
        )
        self.fields["supplier"].empty_label = "Pilih pemasok"
        if not self.instance.pk:
            self.fields["akun_kas_bayar"].initial = Akun.objects.filter(kode_akun="11102").first()
