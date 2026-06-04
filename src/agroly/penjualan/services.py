from decimal import Decimal

from django.db import transaction

from agroly.akuntansi.kode_akun import KAS_BANK, PIUTANG_USAHA, PENDAPATAN_PENJUALAN
from agroly.akuntansi.models import Akun, JurnalHeader
from agroly.akuntansi.services import BarisJurnal, ServiceJurnal
from agroly.persediaan.models import MutasiPersediaan

from .models import PenerimaanPiutang, PenjualanBarang, PenjualanDetail


class ServicePenjualan:
    @staticmethod
    def _akun(kode: str) -> Akun:
        return Akun.objects.get(kode_akun=kode)

    @staticmethod
    def _hitung_total_setelah_diskon_pajak(
        subtotal: Decimal, diskon_persen: Decimal, pajak_persen: Decimal
    ) -> Decimal:
        diskon_nilai = subtotal * ((diskon_persen or Decimal("0")) / Decimal("100"))
        dasar_pajak = subtotal - diskon_nilai
        pajak_nilai = dasar_pajak * ((pajak_persen or Decimal("0")) / Decimal("100"))
        return dasar_pajak + pajak_nilai

    @staticmethod
    def _nomor_jurnal_penjualan(nomor_invoice: str) -> str:
        return f"JUAL-{nomor_invoice}"

    @staticmethod
    def _nomor_jurnal_penerimaan(nomor_bukti: str) -> str:
        return f"PIUTANG-{nomor_bukti}"

    @staticmethod
    @transaction.atomic
    def sinkron_penjualan(
        penjualan: PenjualanBarang,
        barang,
        jumlah: Decimal,
        harga_satuan: Decimal,
        *,
        nomor_invoice_lama: str | None = None,
    ) -> None:
        ServicePenjualan.hapus_dampak(penjualan, nomor_invoice_lama=nomor_invoice_lama)
        subtotal = jumlah * harga_satuan
        PenjualanDetail.objects.create(
            penjualan=penjualan,
            barang=barang,
            jumlah=jumlah,
            harga_satuan=harga_satuan,
            subtotal=subtotal,
        )
        penjualan.total = ServicePenjualan._hitung_total_setelah_diskon_pajak(
            subtotal, penjualan.diskon_persen, penjualan.pajak_persen
        )
        penjualan.save(update_fields=["total"])

        if penjualan.status_pembayaran == "tunai":
            akun_debit = ServicePenjualan._akun(KAS_BANK)
        else:
            akun_debit = ServicePenjualan._akun(PIUTANG_USAHA)
        akun_pendapatan = ServicePenjualan._akun(PENDAPATAN_PENJUALAN)

        ServiceJurnal.posting_jurnal_otomatis(
            tanggal=penjualan.tanggal,
            nomor_bukti=ServicePenjualan._nomor_jurnal_penjualan(penjualan.nomor_invoice),
            keterangan=f"Penjualan {penjualan.nomor_invoice}",
            sumber_transaksi="penjualan",
            daftar_baris=[
                BarisJurnal(akun=akun_debit, debit=penjualan.total, kredit=Decimal("0")),
                BarisJurnal(akun=akun_pendapatan, debit=Decimal("0"), kredit=penjualan.total),
            ],
        )

        for detail in penjualan.detail_penjualan.all():
            if detail.barang.stok < detail.jumlah:
                raise ValueError(
                    f"Stok barang {detail.barang.nama_barang} tidak mencukupi untuk penjualan."
                )
            detail.barang.stok -= detail.jumlah
            detail.barang.save(update_fields=["stok"])
            MutasiPersediaan.objects.create(
                tanggal=penjualan.tanggal,
                barang=detail.barang,
                tipe_mutasi="keluar",
                jumlah=detail.jumlah,
                saldo_setelah=detail.barang.stok,
                keterangan=f"Penjualan {penjualan.nomor_invoice}",
            )

    @staticmethod
    @transaction.atomic
    def hapus_dampak(penjualan: PenjualanBarang, *, nomor_invoice_lama: str | None = None) -> None:
        nomor = nomor_invoice_lama or penjualan.nomor_invoice
        for detail in penjualan.detail_penjualan.select_related("barang").all():
            detail.barang.stok += detail.jumlah
            detail.barang.save(update_fields=["stok"])
        MutasiPersediaan.objects.filter(keterangan=f"Penjualan {nomor}").delete()
        ServiceJurnal.hapus_berdasarkan_nomor_bukti(ServicePenjualan._nomor_jurnal_penjualan(nomor))
        penjualan.detail_penjualan.all().delete()

    @staticmethod
    @transaction.atomic
    def sinkron_penerimaan_piutang(
        data: PenerimaanPiutang,
        *,
        nomor_bukti_lama: str | None = None,
    ) -> None:
        ServicePenjualan.hapus_dampak_penerimaan_piutang(data, nomor_bukti_lama=nomor_bukti_lama)
        akun_kas = data.akun_kas_setoran or ServicePenjualan._akun(KAS_BANK)
        akun_piutang = ServicePenjualan._akun(PIUTANG_USAHA)
        jumlah_bersih = (data.jumlah_terima or Decimal("0")) - (data.diskon or Decimal("0"))
        ServiceJurnal.posting_jurnal_otomatis(
            tanggal=data.tanggal,
            nomor_bukti=ServicePenjualan._nomor_jurnal_penerimaan(data.nomor_bukti),
            keterangan=f"Penerimaan Piutang {data.nomor_bukti}",
            sumber_transaksi="penerimaan_piutang",
            daftar_baris=[
                BarisJurnal(akun=akun_kas, debit=jumlah_bersih, kredit=Decimal("0")),
                BarisJurnal(akun=akun_piutang, debit=Decimal("0"), kredit=jumlah_bersih),
            ],
        )

    @staticmethod
    @transaction.atomic
    def hapus_dampak_penerimaan_piutang(
        data: PenerimaanPiutang, *, nomor_bukti_lama: str | None = None
    ) -> None:
        nomor = nomor_bukti_lama or data.nomor_bukti
        ServiceJurnal.hapus_berdasarkan_nomor_bukti(ServicePenjualan._nomor_jurnal_penerimaan(nomor))
