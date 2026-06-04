from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AkunViewSet,
    BarangViewSet,
    CustomerViewSet,
    JurnalViewSet,
    LaporanBukuBesarApi,
    LaporanNeracaSaldoApi,
    ProduksiPanenViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register("akun", AkunViewSet, basename="akun")
router.register("jurnal", JurnalViewSet, basename="jurnal")
router.register("barang", BarangViewSet, basename="barang")
router.register("customer", CustomerViewSet, basename="customer")
router.register("supplier", SupplierViewSet, basename="supplier")
router.register("produksi-panen", ProduksiPanenViewSet, basename="produksi-panen")

urlpatterns = [
    path("", include(router.urls)),
    path("laporan/buku-besar/", LaporanBukuBesarApi.as_view(), name="api-buku-besar"),
    path("laporan/neraca-saldo/", LaporanNeracaSaldoApi.as_view(), name="api-neraca-saldo"),
]
