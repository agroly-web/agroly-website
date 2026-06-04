from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import CustomerForm, SupplierForm
from .models import Customer, Supplier


class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = "relasi_bisnis/customer_list.html"
    context_object_name = "data_customer"

    def get_queryset(self):
        return Customer.objects.order_by("numbering", "id")


class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = "relasi_bisnis/supplier_list.html"
    context_object_name = "data_supplier"

    def get_queryset(self):
        return Supplier.objects.order_by("numbering", "id")


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "relasi_bisnis/customer_form.html"
    success_url = reverse_lazy("relasi_bisnis:customer")


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "relasi_bisnis/customer_form.html"
    success_url = reverse_lazy("relasi_bisnis:customer")


class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    success_url = reverse_lazy("relasi_bisnis:customer")


class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "relasi_bisnis/supplier_form.html"
    success_url = reverse_lazy("relasi_bisnis:supplier")


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "relasi_bisnis/supplier_form.html"
    success_url = reverse_lazy("relasi_bisnis:supplier")


class SupplierDeleteView(LoginRequiredMixin, DeleteView):
    model = Supplier
    success_url = reverse_lazy("relasi_bisnis:supplier")
