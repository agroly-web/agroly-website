from django.urls import path

from .views import (
    ProduksiPanenCreateView,
    ProduksiPanenDeleteView,
    ProduksiPanenListView,
    ProduksiPanenUpdateView,
)

app_name = "produksi_panen"

urlpatterns = [
    path("", ProduksiPanenListView.as_view(), name="list"),
    path("tambah/", ProduksiPanenCreateView.as_view(), name="tambah"),
    path("<int:pk>/edit/", ProduksiPanenUpdateView.as_view(), name="edit"),
    path("<int:pk>/hapus/", ProduksiPanenDeleteView.as_view(), name="hapus"),
]
