from decimal import Decimal

from django.db import transaction

from agroly.akuntansi.services import ServiceJurnal

from .models import BarangPersediaan, MutasiPersediaan


class ServicePersediaan:
    """Penyesuaian/mutasi persediaan: hanya update stok. Tidak posting jurnal otomatis."""

    @staticmethod
    @transaction.atomic
    def sinkron_mutasi(mutasi: MutasiPersediaan, mutasi_sebelumnya: MutasiPersediaan | None = None) -> None:
        if mutasi_sebelumnya:
            ServicePersediaan.hapus_dampak_mutasi(mutasi_sebelumnya)

        barang = BarangPersediaan.objects.select_for_update().get(pk=mutasi.barang_id)
        mutasi.barang = barang
        jumlah = mutasi.jumlah or Decimal("0")
        stok_awal = barang.stok or Decimal("0")
        if mutasi.tipe_mutasi == "keluar":
            if stok_awal < jumlah:
                raise ValueError("Stok tidak mencukupi untuk mutasi keluar.")
            stok_baru = stok_awal - jumlah
        else:
            stok_baru = stok_awal + jumlah

        barang.stok = stok_baru
        barang.save(update_fields=["stok"])
        mutasi.saldo_setelah = stok_baru
        mutasi.save(update_fields=["saldo_setelah"])

    @staticmethod
    @transaction.atomic
    def hapus_dampak_mutasi(mutasi: MutasiPersediaan) -> None:
        barang = BarangPersediaan.objects.get(pk=mutasi.barang_id)
        if mutasi.tipe_mutasi == "keluar":
            barang.stok = (barang.stok or Decimal("0")) + (mutasi.jumlah or Decimal("0"))
        else:
            barang.stok = (barang.stok or Decimal("0")) - (mutasi.jumlah or Decimal("0"))
        if barang.stok < 0:
            barang.stok = Decimal("0")
        barang.save(update_fields=["stok"])
        ServiceJurnal.hapus_berdasarkan_nomor_bukti(f"MUTASI-{mutasi.id}")
