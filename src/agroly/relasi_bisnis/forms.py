from django import forms

from .models import Customer, Supplier


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["numbering", "nama", "alamat", "telepon", "saldo_saat_ini", "aktif"]
        widgets = {
            "numbering": forms.TextInput(attrs={"class": "form-control", "readonly": True}),
            "nama": forms.TextInput(attrs={"class": "form-control"}),
            "alamat": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "telepon": forms.TextInput(attrs={"class": "form-control"}),
            "saldo_saat_ini": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "aktif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["numbering"].label = "Numbering"
        if not self.instance.pk:
            self.fields["numbering"].initial = Customer.generate_next_numbering()


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["numbering", "nama", "alamat", "telepon", "saldo_saat_ini", "aktif"]
        widgets = {
            "numbering": forms.TextInput(attrs={"class": "form-control", "readonly": True}),
            "nama": forms.TextInput(attrs={"class": "form-control"}),
            "alamat": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "telepon": forms.TextInput(attrs={"class": "form-control"}),
            "saldo_saat_ini": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "aktif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["numbering"].label = "Numbering"
        if not self.instance.pk:
            self.fields["numbering"].initial = Supplier.generate_next_numbering()
