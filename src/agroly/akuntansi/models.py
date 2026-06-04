from django.db import models


class Akun(models.Model):
    KATEGORI_AKUN = (
        ("aset", "Aset"),
        ("kewajiban", "Kewajiban"),
        ("ekuitas", "Ekuitas"),
        ("pendapatan", "Pendapatan"),
        ("hpp", "HPP"),
        ("beban_operasional", "Beban Operasional"),
        ("pendapatan_lain", "Pendapatan Lain-lain"),
        ("beban_lain", "Beban Lain-lain"),
    )

    kode_akun = models.CharField(max_length=10, unique=True)
    nama_akun = models.CharField(max_length=150)
    kategori_akun = models.CharField(max_length=30, choices=KATEGORI_AKUN)
    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "akun"
        ordering = ["kode_akun"]

    def __str__(self) -> str:
        return f"{self.kode_akun} - {self.nama_akun}"


class JurnalHeader(models.Model):
    tanggal = models.DateField()
    nomor_bukti = models.CharField(max_length=50, unique=True, blank=True, null=True)
    keterangan = models.CharField(max_length=255, blank=True)
    sumber_transaksi = models.CharField(max_length=50, default="manual")

    class Meta:
        db_table = "jurnal_header"
        ordering = ["-tanggal", "-id"]

    def __str__(self) -> str:
        return f"{self.nomor_bukti or '-'} ({self.tanggal})"


class JurnalDetail(models.Model):
    jurnal_header = models.ForeignKey(
        JurnalHeader, related_name="detail_jurnal", on_delete=models.CASCADE
    )
    akun = models.ForeignKey(Akun, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    kredit = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        db_table = "jurnal_detail"

    def __str__(self) -> str:
        return f"{self.jurnal_header.nomor_bukti} - {self.akun.kode_akun}"
