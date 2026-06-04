from decimal import Decimal

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from .form_helpers import siapkan_field_akun
from .models import Akun, JurnalDetail, JurnalHeader

WIDGET_INPUT = {"class": "form-control"}
WIDGET_SELECT = {"class": "form-select"}


class AkunForm(forms.ModelForm):
    class Meta:
        model = Akun
        fields = ["kode_akun", "nama_akun", "kategori_akun", "aktif"]


class JurnalHeaderForm(forms.ModelForm):
    class Meta:
        model = JurnalHeader
        fields = ["tanggal", "nomor_bukti", "keterangan", "sumber_transaksi"]
        widgets = {
            "tanggal": forms.DateInput(attrs={**WIDGET_INPUT, "type": "date"}),
            "nomor_bukti": forms.TextInput(attrs=WIDGET_INPUT),
            "keterangan": forms.TextInput(attrs=WIDGET_INPUT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nomor_bukti"].required = False
        self.fields["sumber_transaksi"].required = False
        self.fields["sumber_transaksi"].widget = forms.HiddenInput()


class JurnalDetailForm(forms.ModelForm):
    POSISI_CHOICES = (
        ("debit", "Debit"),
        ("kredit", "Kredit"),
    )

    posisi = forms.ChoiceField(
        choices=POSISI_CHOICES,
        required=False,
        widget=forms.Select(attrs=WIDGET_SELECT),
    )
    nominal = forms.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={**WIDGET_INPUT, "step": "0.01", "placeholder": "0"}),
    )

    class Meta:
        model = JurnalDetail
        fields = ("akun",)
        widgets = {
            "akun": forms.Select(attrs=WIDGET_SELECT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        siapkan_field_akun(self.fields["akun"])
        self.fields["posisi"].empty_label = "Pilih posisi"
        self.fields["akun"].required = False

        if self.instance and self.instance.pk:
            if (self.instance.debit or 0) > 0:
                self.fields["posisi"].initial = "debit"
                self.fields["nominal"].initial = self.instance.debit
            else:
                self.fields["posisi"].initial = "kredit"
                self.fields["nominal"].initial = self.instance.kredit

        if not self.instance.pk:
            self.empty_permitted = True

    def _baris_kosong(self, cleaned) -> bool:
        if cleaned.get("DELETE"):
            return False
        akun = cleaned.get("akun")
        nominal = cleaned.get("nominal")
        return not akun and (nominal in (None, "") or nominal == 0)

    def clean_nominal(self):
        nominal = self.cleaned_data.get("nominal")
        if nominal in (None, ""):
            return None
        return nominal

    def has_changed(self):
        if self.data:
            akun = self.data.get(f"{self.prefix}-akun", "")
            nominal = self.data.get(f"{self.prefix}-nominal", "")
            if not akun and not nominal:
                return False
        return super().has_changed()

    def clean(self):
        cleaned = super().clean()
        if self._baris_kosong(cleaned):
            return cleaned

        akun = cleaned.get("akun")
        posisi = cleaned.get("posisi")
        nominal = cleaned.get("nominal")

        if not akun:
            raise forms.ValidationError("Akun wajib dipilih.")
        if not posisi:
            raise forms.ValidationError("Pilih posisi Debit atau Kredit.")
        if nominal is None or nominal <= 0:
            raise forms.ValidationError("Nominal wajib lebih besar dari nol.")

        if posisi == "debit":
            cleaned["debit"] = nominal
            cleaned["kredit"] = Decimal("0")
        else:
            cleaned["debit"] = Decimal("0")
            cleaned["kredit"] = nominal
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        posisi = self.cleaned_data.get("posisi")
        nominal = self.cleaned_data.get("nominal") or Decimal("0")
        if not self.cleaned_data.get("akun"):
            if commit:
                return instance
            return instance
        if posisi == "debit":
            instance.debit = nominal
            instance.kredit = Decimal("0")
        else:
            instance.debit = Decimal("0")
            instance.kredit = nominal
        if commit:
            instance.save()
        return instance


class BaseJurnalDetailFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        baris_valid = 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            if not form.cleaned_data.get("akun"):
                continue
            baris_valid += 1

        if baris_valid < 2:
            raise forms.ValidationError("Jurnal harus memiliki minimal dua baris detail.")


JurnalDetailFormSet = inlineformset_factory(
    JurnalHeader,
    JurnalDetail,
    form=JurnalDetailForm,
    formset=BaseJurnalDetailFormSet,
    fields=("akun",),
    extra=2,
    can_delete=True,
)


class JurnalPenyesuaianHeaderForm(forms.ModelForm):
    class Meta:
        model = JurnalHeader
        fields = ["tanggal", "nomor_bukti", "keterangan"]
        labels = {
            "nomor_bukti": "No. Dokumen",
        }
        widgets = {
            "tanggal": forms.DateInput(attrs={**WIDGET_INPUT, "type": "date"}),
            "nomor_bukti": forms.TextInput(
                attrs={**WIDGET_INPUT, "placeholder": "Kosongkan untuk nomor otomatis"}
            ),
            "keterangan": forms.TextInput(attrs=WIDGET_INPUT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nomor_bukti"].required = False
        self.fields["keterangan"].required = False

    def clean_nomor_bukti(self):
        nomor = (self.cleaned_data.get("nomor_bukti") or "").strip()
        if not nomor:
            return None
        duplikat = JurnalHeader.objects.filter(nomor_bukti=nomor)
        if self.instance.pk:
            duplikat = duplikat.exclude(pk=self.instance.pk)
        if duplikat.exists():
            raise forms.ValidationError("No. dokumen sudah digunakan.")
        return nomor


class JurnalPenyesuaianDetailForm(forms.ModelForm):
    class Meta:
        model = JurnalDetail
        fields = ("akun", "debit", "kredit")
        widgets = {
            "akun": forms.Select(attrs=WIDGET_SELECT),
            "debit": forms.NumberInput(
                attrs={**WIDGET_INPUT, "step": "0.01", "min": "0", "placeholder": "0"}
            ),
            "kredit": forms.NumberInput(
                attrs={**WIDGET_INPUT, "step": "0.01", "min": "0", "placeholder": "0"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        siapkan_field_akun(self.fields["akun"])
        self.fields["akun"].required = False
        self.fields["debit"].required = False
        self.fields["kredit"].required = False
        if not self.instance.pk:
            self.empty_permitted = True

    def _baris_kosong(self, cleaned) -> bool:
        if cleaned.get("DELETE"):
            return False
        akun = cleaned.get("akun")
        debit = cleaned.get("debit") or Decimal("0")
        kredit = cleaned.get("kredit") or Decimal("0")
        return not akun and debit == 0 and kredit == 0

    def clean_debit(self):
        debit = self.cleaned_data.get("debit")
        return debit if debit is not None else Decimal("0")

    def clean_kredit(self):
        kredit = self.cleaned_data.get("kredit")
        return kredit if kredit is not None else Decimal("0")

    def has_changed(self):
        if self.data:
            akun = self.data.get(f"{self.prefix}-akun", "")
            debit = self.data.get(f"{self.prefix}-debit", "")
            kredit = self.data.get(f"{self.prefix}-kredit", "")
            if not akun and not debit and not kredit:
                return False
        return super().has_changed()

    def clean(self):
        cleaned = super().clean()
        if self._baris_kosong(cleaned):
            return cleaned

        akun = cleaned.get("akun")
        debit = cleaned.get("debit") or Decimal("0")
        kredit = cleaned.get("kredit") or Decimal("0")

        if not akun:
            raise forms.ValidationError("Akun wajib dipilih.")
        if debit < 0 or kredit < 0:
            raise forms.ValidationError("Nilai debit/kredit tidak boleh negatif.")
        if debit > 0 and kredit > 0:
            raise forms.ValidationError("Isi debit atau kredit, bukan keduanya.")
        if debit == 0 and kredit == 0:
            raise forms.ValidationError("Isi nominal debit atau kredit.")
        return cleaned


class BaseJurnalPenyesuaianDetailFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        baris_valid = 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            if not form.cleaned_data.get("akun"):
                continue
            baris_valid += 1

        if baris_valid < 2:
            raise forms.ValidationError("Jurnal penyesuaian minimal dua baris detail.")


JurnalPenyesuaianDetailFormSet = inlineformset_factory(
    JurnalHeader,
    JurnalDetail,
    form=JurnalPenyesuaianDetailForm,
    formset=BaseJurnalPenyesuaianDetailFormSet,
    fields=("akun", "debit", "kredit"),
    extra=2,
    can_delete=True,
)
