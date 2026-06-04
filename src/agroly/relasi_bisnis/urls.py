from django.urls import path

from .views import (
    CustomerCreateView,
    CustomerDeleteView,
    CustomerListView,
    CustomerUpdateView,
    SupplierCreateView,
    SupplierDeleteView,
    SupplierListView,
    SupplierUpdateView,
)

app_name = "relasi_bisnis"

urlpatterns = [
    path("customer/", CustomerListView.as_view(), name="customer"),
    path("customer/tambah/", CustomerCreateView.as_view(), name="tambah_customer"),
    path("customer/<int:pk>/edit/", CustomerUpdateView.as_view(), name="edit_customer"),
    path("customer/<int:pk>/hapus/", CustomerDeleteView.as_view(), name="hapus_customer"),
    path("supplier/", SupplierListView.as_view(), name="supplier"),
    path("supplier/tambah/", SupplierCreateView.as_view(), name="tambah_supplier"),
    path("supplier/<int:pk>/edit/", SupplierUpdateView.as_view(), name="edit_supplier"),
    path("supplier/<int:pk>/hapus/", SupplierDeleteView.as_view(), name="hapus_supplier"),
]
