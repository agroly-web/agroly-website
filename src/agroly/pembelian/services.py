from decimal import Decimal

from django.db import transaction

from agroly.akuntansi.kode_akun import KAS_BANK, PERLENGKAPAN, UTANG_USAHA
from agroly.akuntansi.models import Akun, JurnalHeader
from agroly.akuntansi.services import BarisJurnal, ServiceJurnal
from agroly.persediaan.models import MutasiPersediaan

from .models import PembayaranUtang, PembelianBarang, PembelianDetail


class ServicePembelian:
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
    def _nomor_jurnal_pembelian(nomor_invoice: str) -> str:
        return f"BELI-{nomor_invoice}"

    @staticmethod
    def _nomor_jurnal_pembayaran(nomor_bukti: str) -> str:
        return f"UTANG-{nomor_bukti}"

    @staticmethod
    @transaction.atomic
    def sinkron_pembelian(
        pembelian: PembelianBarang,
        barang,
        jumlah: Decimal,
        harga_satuan: Decimal,
        *,
        nomor_invoice_lama: str | None = None,
    ) -> None:
        ServicePembelian.hapus_dampak(pembelian, nomor_invoice_lama=nomor_invoice_lama)
        subtotal = jumlah * harga_satuan
        PembelianDetail.objects.create(
            pembelian=pembelian,
            barang=barang,
            jumlah=jumlah,
            harga_satuan=harga_satuan,
            subtotal=subtotal,
        )
        pembelian.total = ServicePembelian._hitung_total_setelah_diskon_pajak(
            subtotal, pembelian.diskon_persen, pembelian.pajak_persen
        )
        pembelian.save(update_fields=["total"])

        akun_perlengkapan = ServicePembelian._akun(PERLENGKAPAN)
        if pembelian.status_pembayaran == "tunai":
            akun_kredit = ServicePembelian._akun(KAS_BANK)
        else:
            akun_kredit = ServicePembelian._akun(UTANG_USAHA)

        ServiceJurnal.posting_jurnal_otomatis(
            tanggal=pembelian.tanggal,
            nomor_bukti=ServicePembelian._nomor_jurnal_pembelian(pembelian.nomor_invoice),
            keterangan=f"Pembelian {pembelian.nomor_invoice}",
            sumber_transaksi="pembelian",
            daftar_baris=[
                BarisJurnal(akun=akun_perlengkapan, debit=pembelian.total, kredit=Decimal("0")),
                BarisJurnal(akun=akun_kredit, debit=Decimal("0"), kredit=pembelian.total),
            ],
        )

        for detail in pembelian.detail_pembelian.all():
            detail.barang.stok += detail.jumlah
            detail.barang.save(update_fields=["stok"])
            MutasiPersediaan.objects.create(
                tanggal=pembelian.tanggal,
                barang=detail.barang,
                tipe_mutasi="masuk",
                jumlah=detail.jumlah,
                saldo_setelah=detail.barang.stok,
                keterangan=f"Pembelian {pembelian.nomor_invoice}",
            )

    @staticmethod
    @transaction.atomic
    def hapus_dampak(pembelian: PembelianBarang, *, nomor_invoice_lama: str | None = None) -> None:
        nomor = nomor_invoice_lama or pembelian.nomor_invoice
        for detail in pembelian.detail_pembelian.select_related("barang").all():
            detail.barang.stok -= detail.jumlah
            detail.barang.save(update_fields=["stok"])
        MutasiPersediaan.objects.filter(keterangan=f"Pembelian {nomor}").delete()
        ServiceJurnal.hapus_berdasarkan_nomor_bukti(
            ServicePembelian._nomor_jurnal_pembelian(nomor)
        )
        pembelian.detail_pembelian.all().delete()

    @staticmethod
    @transaction.atomic
    def sinkron_pembayaran_utang(
        data: PembayaranUtang,
        *,
        nomor_bukti_lama: str | None = None,
    ) -> None:
        ServicePembelian.hapus_dampak_pembayaran_utang(data, nomor_bukti_lama=nomor_bukti_lama)
        akun_utang = ServicePembelian._akun(UTANG_USAHA)
        akun_kas = data.akun_kas_bayar or ServicePembelian._akun(KAS_BANK)
        jumlah_bersih = (data.jumlah_bayar or Decimal("0")) - (data.diskon or Decimal("0"))
        ServiceJurnal.posting_jurnal_otomatis(
            tanggal=data.tanggal,
            nomor_bukti=ServicePembelian._nomor_jurnal_pembayaran(data.nomor_bukti),
            keterangan=f"Pembayaran Utang {data.nomor_bukti}",
            sumber_transaksi="pembayaran_utang",
            daftar_baris=[
                BarisJurnal(akun=akun_utang, debit=jumlah_bersih, kredit=Decimal("0")),
                BarisJurnal(akun=akun_kas, debit=Decimal("0"), kredit=jumlah_bersih),
            ],
        )

    @staticmethod
    @transaction.atomic
    def hapus_dampak_pembayaran_utang(
        data: PembayaranUtang, *, nomor_bukti_lama: str | None = None
    ) -> None:
        nomor = nomor_bukti_lama or data.nomor_bukti
        ServiceJurnal.hapus_berdasarkan_nomor_bukti(
            ServicePembelian._nomor_jurnal_pembayaran(nomor)
        )
