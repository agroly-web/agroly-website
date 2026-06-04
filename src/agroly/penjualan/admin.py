from django.contrib import admin

from .models import PenerimaanPiutang, PenjualanBarang, PenjualanDetail

admin.site.register(PenjualanBarang)
admin.site.register(PenjualanDetail)
admin.site.register(PenerimaanPiutang)
