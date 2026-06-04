from django.db import models

from agroly.persediaan.models import BarangPersediaan
from agroly.relasi_bisnis.models import Customer


class PenjualanBarang(models.Model):
    STATUS_PEMBAYARAN = (
        ("tunai", "Tunai"),
        ("piutang", "Piutang"),
    )

    tanggal = models.DateField()
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    nomor_invoice = models.CharField(max_length=50, unique=True)
    termin_pembayaran = models.CharField(max_length=50, blank=True)
    diskon_persen = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pajak_persen = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=18, decimal_places=2)
    status_pembayaran = models.CharField(max_length=20, choices=STATUS_PEMBAYARAN)
    keterangan = models.CharField(max_length=255, blank=True)

    def ppn_untuk_subtotal(self, subtotal):
        from decimal import Decimal

        diskon_nilai = subtotal * ((self.diskon_persen or Decimal("0")) / Decimal("100"))
        dasar_pajak = subtotal - diskon_nilai
        return dasar_pajak * ((self.pajak_persen or Decimal("0")) / Decimal("100"))

    def jumlah_untuk_subtotal(self, subtotal):
        from decimal import Decimal

        diskon_nilai = subtotal * ((self.diskon_persen or Decimal("0")) / Decimal("100"))
        dasar_pajak = subtotal - diskon_nilai
        pajak_nilai = dasar_pajak * ((self.pajak_persen or Decimal("0")) / Decimal("100"))
        return dasar_pajak + pajak_nilai

    class Meta:
        db_table = "penjualan_barang"
        ordering = ["-tanggal", "-id"]


class PenjualanDetail(models.Model):
    penjualan = models.ForeignKey(
        PenjualanBarang, related_name="detail_penjualan", on_delete=models.CASCADE
    )
    barang = models.ForeignKey(BarangPersediaan, on_delete=models.PROTECT)
    jumlah = models.DecimalField(max_digits=18, decimal_places=2)
    harga_satuan = models.DecimalField(max_digits=18, decimal_places=2)
    subtotal = models.DecimalField(max_digits=18, decimal_places=2)

    @property
    def ppn_nilai(self):
        return self.penjualan.ppn_untuk_subtotal(self.subtotal)

    @property
    def jumlah_akhir(self):
        return self.penjualan.jumlah_untuk_subtotal(self.subtotal)

    class Meta:
        db_table = "penjualan_detail"


class PenerimaanPiutang(models.Model):
    tanggal = models.DateField()
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    akun_kas_setoran = models.ForeignKey(
        "akuntansi.Akun",
        on_delete=models.PROTECT,
        related_name="penerimaan_piutang_setoran",
        null=True,
        blank=True,
    )
    faktur_no = models.CharField(max_length=50, blank=True)
    nomor_bukti = models.CharField(max_length=50, unique=True)
    jumlah_terima = models.DecimalField(max_digits=18, decimal_places=2)
    diskon = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    keterangan = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "penerimaan_piutang"
