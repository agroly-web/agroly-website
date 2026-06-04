from django.contrib import admin

from .models import PembayaranUtang, PembelianBarang, PembelianDetail

admin.site.register(PembelianBarang)
admin.site.register(PembelianDetail)
admin.site.register(PembayaranUtang)
