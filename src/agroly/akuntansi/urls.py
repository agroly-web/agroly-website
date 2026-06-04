from django.urls import path
from django.views.generic import RedirectView

from .views import (
    AkunCreateView,
    AkunDeleteView,
    AkunListView,
    AkunUpdateView,
    JurnalCreateView,
    JurnalDeleteView,
    JurnalListView,
    JurnalPenyesuaianCreateView,
    JurnalPenyesuaianDeleteView,
    JurnalPenyesuaianListView,
    JurnalPenyesuaianUpdateView,
    JurnalUpdateView,
    LaporanArusKasView,
    LaporanLabaRugiView,
    LaporanNeracaView,
)

app_name = "akuntansi"

urlpatterns = [
    path("daftar-akun/", AkunListView.as_view(), name="daftar_akun"),
    path("daftar-akun/tambah/", AkunCreateView.as_view(), name="tambah_akun"),
    path("daftar-akun/<int:pk>/edit/", AkunUpdateView.as_view(), name="edit_akun"),
    path("daftar-akun/<int:pk>/hapus/", AkunDeleteView.as_view(), name="hapus_akun"),
    path("jurnal/", JurnalListView.as_view(), name="daftar_jurnal"),
    path("jurnal/tambah/", JurnalCreateView.as_view(), name="tambah_jurnal"),
    path("jurnal/<int:pk>/edit/", JurnalUpdateView.as_view(), name="edit_jurnal"),
    path("jurnal/<int:pk>/hapus/", JurnalDeleteView.as_view(), name="hapus_jurnal"),
    path("jurnal-penyesuaian/", JurnalPenyesuaianListView.as_view(), name="daftar_penyesuaian"),
    path(
        "jurnal-penyesuaian/tambah/",
        JurnalPenyesuaianCreateView.as_view(),
        name="tambah_penyesuaian",
    ),
    path(
        "jurnal-penyesuaian/<int:pk>/edit/",
        JurnalPenyesuaianUpdateView.as_view(),
        name="edit_penyesuaian",
    ),
    path(
        "jurnal-penyesuaian/<int:pk>/hapus/",
        JurnalPenyesuaianDeleteView.as_view(),
        name="hapus_penyesuaian",
    ),
    path("laporan/", RedirectView.as_view(pattern_name="akuntansi:laporan_laba_rugi", permanent=False)),
    path("laporan/laba-rugi/", LaporanLabaRugiView.as_view(), name="laporan_laba_rugi"),
    path("laporan/posisi-keuangan/", LaporanNeracaView.as_view(), name="laporan_neraca"),
    path("laporan/arus-kas/", LaporanArusKasView.as_view(), name="laporan_arus_kas"),
]
