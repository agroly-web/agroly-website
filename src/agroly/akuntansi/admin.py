from django.contrib import admin

from .models import Akun, JurnalDetail, JurnalHeader

admin.site.register(Akun)
admin.site.register(JurnalHeader)
admin.site.register(JurnalDetail)
