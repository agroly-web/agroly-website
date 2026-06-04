import re

from django.db import models


class Customer(models.Model):
    numbering = models.CharField(max_length=20, unique=True, blank=True)
    nama = models.CharField(max_length=150)
    no_kartu = models.CharField(max_length=50, blank=True)
    alamat = models.TextField(blank=True)
    telepon = models.CharField(max_length=30, blank=True)
    saldo_saat_ini = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "customer"
        verbose_name = "Customer"
        verbose_name_plural = "Customer"

    def __str__(self) -> str:
        return self.nama

    @classmethod
    def generate_next_numbering(cls) -> str:
        prefix = "C-"
        numbers = []
        for code in cls.objects.filter(numbering__startswith=prefix).values_list("numbering", flat=True):
            match = re.fullmatch(r"C-(\d+)", code)
            if match:
                numbers.append(int(match.group(1)))
        next_num = (max(numbers) if numbers else 0) + 1
        return f"{prefix}{next_num:02d}"

    def save(self, *args, **kwargs):
        if not self.numbering:
            self.numbering = self.generate_next_numbering()
        super().save(*args, **kwargs)


class Supplier(models.Model):
    numbering = models.CharField(max_length=20, unique=True, blank=True)
    nama = models.CharField(max_length=150)
    no_kartu = models.CharField(max_length=50, blank=True)
    alamat = models.TextField(blank=True)
    telepon = models.CharField(max_length=30, blank=True)
    saldo_saat_ini = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "supplier"
        verbose_name = "Supplier"
        verbose_name_plural = "Supplier"

    def __str__(self) -> str:
        return self.nama

    @classmethod
    def generate_next_numbering(cls) -> str:
        prefix = "S-"
        numbers = []
        for code in cls.objects.filter(numbering__startswith=prefix).values_list("numbering", flat=True):
            match = re.fullmatch(r"S-(\d+)", code)
            if match:
                numbers.append(int(match.group(1)))
        next_num = (max(numbers) if numbers else 0) + 1
        return f"{prefix}{next_num:02d}"

    def save(self, *args, **kwargs):
        if not self.numbering:
            self.numbering = self.generate_next_numbering()
        super().save(*args, **kwargs)
