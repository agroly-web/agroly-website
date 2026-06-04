from rest_framework import serializers

from agroly.akuntansi.models import Akun, JurnalDetail, JurnalHeader
from agroly.persediaan.models import BarangPersediaan
from agroly.produksi_panen.models import ProduksiPanen
from agroly.relasi_bisnis.models import Customer, Supplier


class AkunSerializer(serializers.ModelSerializer):
    class Meta:
        model = Akun
        fields = "__all__"


class JurnalDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = JurnalDetail
        fields = "__all__"


class JurnalHeaderSerializer(serializers.ModelSerializer):
    detail_jurnal = JurnalDetailSerializer(many=True, read_only=True)

    class Meta:
        model = JurnalHeader
        fields = "__all__"


class BarangPersediaanSerializer(serializers.ModelSerializer):
    class Meta:
        model = BarangPersediaan
        fields = "__all__"


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class ProduksiPanenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProduksiPanen
        fields = "__all__"
