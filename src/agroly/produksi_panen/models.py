from django.db import models


class ProduksiPanen(models.Model):
    tanggal = models.DateField()
    komoditas = models.CharField(max_length=120)
    grade = models.CharField(max_length=30)
    jumlah_hasil_panen = models.DecimalField(max_digits=18, decimal_places=2)
    satuan = models.CharField(max_length=30, default="kg")
    keterangan = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "produksi_panen"
        ordering = ["-tanggal", "-id"]
