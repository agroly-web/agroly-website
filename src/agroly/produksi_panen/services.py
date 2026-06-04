from decimal import Decimal

from django.db import transaction

from agroly.akuntansi.services import ServiceJurnal
from agroly.persediaan.models import BarangPersediaan, MutasiPersediaan

from .models import ProduksiPanen


class ServiceProduksiPanen:
    """Produksi panen: hanya menambah stok persediaan. Tidak posting jurnal otomatis."""

    @staticmethod
    def _nama_barang_dari_produksi(data: ProduksiPanen) -> str:
        return f"{data.komoditas} Grade {data.grade}".strip()

    @staticmethod
    def _ambil_atau_buat_barang(data: ProduksiPanen) -> BarangPersediaan:
        nama_barang = ServiceProduksiPanen._nama_barang_dari_produksi(data)
        barang = BarangPersediaan.objects.filter(nama_barang=data.komoditas).first()
        if barang:
            return barang
        barang = BarangPersediaan.objects.filter(nama_barang=nama_barang).first()
        if barang:
            return barang

        basis_kode = (
            f"PANEN-{(data.komoditas or 'KOM').upper().replace(' ', '')[:10]}"
            f"-{(data.grade or 'X').upper()[:5]}"
        )
        kandidat = basis_kode
        urutan = 1
        while BarangPersediaan.objects.filter(kode_barang=kandidat).exists():
            urutan += 1
            kandidat = f"{basis_kode[:24]}-{urutan}"

        return BarangPersediaan.objects.create(
            kode_barang=kandidat,
            nama_barang=nama_barang,
            stok=Decimal("0"),
            satuan=data.satuan or "kg",
            harga_beli=Decimal("0"),
            harga_jual=Decimal("0"),
            aktif=True,
        )

    @staticmethod
    @transaction.atomic
    def sinkron_produksi(data: ProduksiPanen) -> None:
        ServiceProduksiPanen.hapus_dampak_produksi(data)
        barang = ServiceProduksiPanen._ambil_atau_buat_barang(data)
        jumlah_panen = data.jumlah_hasil_panen or Decimal("0")

        barang.stok = (barang.stok or Decimal("0")) + jumlah_panen
        barang.save(update_fields=["stok"])
        MutasiPersediaan.objects.create(
            tanggal=data.tanggal,
            barang=barang,
            tipe_mutasi="masuk",
            jumlah=jumlah_panen,
            saldo_setelah=barang.stok,
            keterangan=f"Produksi panen {data.id}",
        )

    @staticmethod
    @transaction.atomic
    def hapus_dampak_produksi(data: ProduksiPanen) -> None:
        for mutasi in MutasiPersediaan.objects.filter(keterangan=f"Produksi panen {data.id}").select_related(
            "barang"
        ):
            mutasi.barang.stok = (mutasi.barang.stok or Decimal("0")) - (mutasi.jumlah or Decimal("0"))
            if mutasi.barang.stok < 0:
                mutasi.barang.stok = Decimal("0")
            mutasi.barang.save(update_fields=["stok"])
        MutasiPersediaan.objects.filter(keterangan=f"Produksi panen {data.id}").delete()
        ServiceJurnal.hapus_berdasarkan_nomor_bukti(f"PRODUKSI-{data.id}")
