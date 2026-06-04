from django.urls import path

from .views import (
    BarangCreateView,
    BarangDeleteView,
    BarangListView,
    BarangUpdateView,
    MutasiCreateView,
    MutasiDeleteView,
    MutasiPersediaanListView,
    MutasiUpdateView,
)

app_name = "persediaan"

urlpatterns = [
    path("barang/", BarangListView.as_view(), name="barang"),
    path("barang/tambah/", BarangCreateView.as_view(), name="tambah_barang"),
    path("barang/<int:pk>/edit/", BarangUpdateView.as_view(), name="edit_barang"),
    path("barang/<int:pk>/hapus/", BarangDeleteView.as_view(), name="hapus_barang"),
    path("penyesuaian/", MutasiPersediaanListView.as_view(), name="penyesuaian"),
    path("penyesuaian/tambah/", MutasiCreateView.as_view(), name="tambah_penyesuaian"),
    path("penyesuaian/<int:pk>/edit/", MutasiUpdateView.as_view(), name="edit_penyesuaian"),
    path("penyesuaian/<int:pk>/hapus/", MutasiDeleteView.as_view(), name="hapus_penyesuaian"),
]
