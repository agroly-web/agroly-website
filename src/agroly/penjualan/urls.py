from django.urls import path

from .views import (
    PenerimaanPiutangCreateView,
    PenerimaanPiutangDeleteView,
    PenerimaanPiutangListView,
    PenerimaanPiutangUpdateView,
    PenjualanCreateView,
    PenjualanDeleteView,
    PenjualanListView,
    PenjualanUpdateView,
)

app_name = "penjualan"

urlpatterns = [
    path("barang/", PenjualanListView.as_view(), name="barang"),
    path("barang/tambah/", PenjualanCreateView.as_view(), name="tambah_barang"),
    path("barang/<int:pk>/edit/", PenjualanUpdateView.as_view(), name="edit_barang"),
    path("barang/<int:pk>/hapus/", PenjualanDeleteView.as_view(), name="hapus_barang"),
    path("penerimaan-piutang/", PenerimaanPiutangListView.as_view(), name="penerimaan_piutang"),
    path("penerimaan-piutang/tambah/", PenerimaanPiutangCreateView.as_view(), name="tambah_piutang"),
    path("penerimaan-piutang/<int:pk>/edit/", PenerimaanPiutangUpdateView.as_view(), name="edit_piutang"),
    path("penerimaan-piutang/<int:pk>/hapus/", PenerimaanPiutangDeleteView.as_view(), name="hapus_piutang"),
]
