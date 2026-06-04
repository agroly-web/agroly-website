from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from agroly.akuntansi.models import Akun, JurnalHeader
from agroly.akuntansi.services import ServiceLaporanKeuangan
from agroly.persediaan.models import BarangPersediaan
from agroly.produksi_panen.models import ProduksiPanen
from agroly.relasi_bisnis.models import Customer, Supplier

from .serializers import (
    AkunSerializer,
    BarangPersediaanSerializer,
    CustomerSerializer,
    JurnalHeaderSerializer,
    ProduksiPanenSerializer,
    SupplierSerializer,
)


class AkunViewSet(ModelViewSet):
    queryset = Akun.objects.all()
    serializer_class = AkunSerializer
    permission_classes = [IsAuthenticated]


class JurnalViewSet(ModelViewSet):
    queryset = JurnalHeader.objects.all()
    serializer_class = JurnalHeaderSerializer
    permission_classes = [IsAuthenticated]


class BarangViewSet(ModelViewSet):
    queryset = BarangPersediaan.objects.all()
    serializer_class = BarangPersediaanSerializer
    permission_classes = [IsAuthenticated]


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]


class SupplierViewSet(ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]


class ProduksiPanenViewSet(ModelViewSet):
    queryset = ProduksiPanen.objects.all()
    serializer_class = ProduksiPanenSerializer
    permission_classes = [IsAuthenticated]


class LaporanBukuBesarApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(ServiceLaporanKeuangan.hitung_buku_besar())


class LaporanNeracaSaldoApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(ServiceLaporanKeuangan.hitung_neraca_saldo())
