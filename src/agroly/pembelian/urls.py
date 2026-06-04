from django.urls import path

from .views import (
    PembayaranUtangCreateView,
    PembayaranUtangDeleteView,
    PembayaranUtangListView,
    PembayaranUtangUpdateView,
    PembelianCreateView,
    PembelianDeleteView,
    PembelianListView,
    PembelianUpdateView,
)

app_name = "pembelian"

urlpatterns = [
    path("barang/", PembelianListView.as_view(), name="barang"),
    path("barang/tambah/", PembelianCreateView.as_view(), name="tambah_barang"),
    path("barang/<int:pk>/edit/", PembelianUpdateView.as_view(), name="edit_barang"),
    path("barang/<int:pk>/hapus/", PembelianDeleteView.as_view(), name="hapus_barang"),
    path("pembayaran-utang/", PembayaranUtangListView.as_view(), name="pembayaran_utang"),
    path("pembayaran-utang/tambah/", PembayaranUtangCreateView.as_view(), name="tambah_utang"),
    path("pembayaran-utang/<int:pk>/edit/", PembayaranUtangUpdateView.as_view(), name="edit_utang"),
    path("pembayaran-utang/<int:pk>/hapus/", PembayaranUtangDeleteView.as_view(), name="hapus_utang"),
]
