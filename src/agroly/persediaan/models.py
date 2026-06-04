from django.db import models


class BarangPersediaan(models.Model):
    kode_barang = models.CharField(max_length=30, unique=True)
    nama_barang = models.CharField(max_length=150)
    stok = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    satuan = models.CharField(max_length=30, default="kg")
    harga_beli = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    harga_jual = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "barang_persediaan"
        verbose_name = "Barang Persediaan"
        verbose_name_plural = "Daftar Barang Persediaan"

    def __str__(self) -> str:
        return f"{self.kode_barang} - {self.nama_barang}"


class MutasiPersediaan(models.Model):
    TIPE_MUTASI = (
        ("masuk", "Masuk"),
        ("keluar", "Keluar"),
        ("penyesuaian", "Penyesuaian"),
    )

    tanggal = models.DateField()
    nomor_dokumen = models.CharField(max_length=50, blank=True)
    barang = models.ForeignKey(BarangPersediaan, on_delete=models.PROTECT)
    tipe_mutasi = models.CharField(max_length=20, choices=TIPE_MUTASI)
    jumlah = models.DecimalField(max_digits=18, decimal_places=2)
    harga_per_unit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    akun = models.ForeignKey("akuntansi.Akun", on_delete=models.PROTECT, null=True, blank=True)
    saldo_setelah = models.DecimalField(max_digits=18, decimal_places=2)
    keterangan = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "mutasi_persediaan"
        verbose_name = "Mutasi Persediaan"
        verbose_name_plural = "Riwayat Mutasi Persediaan"
        ordering = ["-tanggal", "-id"]
