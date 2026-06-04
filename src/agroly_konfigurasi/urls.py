from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path("login/", LoginView.as_view(template_name="autentikasi/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", include("agroly.dashboard.urls")),
    path("akuntansi/", include("agroly.akuntansi.urls")),
    path("relasi-bisnis/", include("agroly.relasi_bisnis.urls")),
    path("persediaan/", include("agroly.persediaan.urls")),
    path("penjualan/", include("agroly.penjualan.urls")),
    path("pembelian/", include("agroly.pembelian.urls")),
    path("produksi-panen/", include("agroly.produksi_panen.urls")),
    path("api/v1/", include("agroly.api.urls")),
]
