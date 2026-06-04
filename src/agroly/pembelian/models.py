from django.db import models

from agroly.persediaan.models import BarangPersediaan
from agroly.relasi_bisnis.models import Supplier


class PembelianBarang(models.Model):
    STATUS_PEMBAYARAN = (
        ("tunai", "Tunai"),
        ("utang", "Utang"),
    )

    tanggal = models.DateField()
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    nomor_invoice = models.CharField(max_length=50, unique=True)
    nomor_faktur_pemasok = models.CharField(max_length=50, blank=True)
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
        db_table = "pembelian_barang"
        ordering = ["-tanggal", "-id"]


class PembelianDetail(models.Model):
    pembelian = models.ForeignKey(
        PembelianBarang, related_name="detail_pembelian", on_delete=models.CASCADE
    )
    barang = models.ForeignKey(BarangPersediaan, on_delete=models.PROTECT)
    jumlah = models.DecimalField(max_digits=18, decimal_places=2)
    harga_satuan = models.DecimalField(max_digits=18, decimal_places=2)
    subtotal = models.DecimalField(max_digits=18, decimal_places=2)

    @property
    def ppn_nilai(self):
        return self.pembelian.ppn_untuk_subtotal(self.subtotal)

    @property
    def jumlah_akhir(self):
        return self.pembelian.jumlah_untuk_subtotal(self.subtotal)

    class Meta:
        db_table = "pembelian_detail"


class PembayaranUtang(models.Model):
    tanggal = models.DateField()
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    akun_kas_bayar = models.ForeignKey(
        "akuntansi.Akun",
        on_delete=models.PROTECT,
        related_name="pembayaran_utang_kas",
        null=True,
        blank=True,
    )
    no_cek = models.CharField(max_length=50, blank=True)
    nomor_bukti = models.CharField(max_length=50, unique=True)
    jumlah_bayar = models.DecimalField(max_digits=18, decimal_places=2)
    diskon = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    keterangan = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "pembayaran_utang"
