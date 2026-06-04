from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import ProduksiPanenForm
from .models import ProduksiPanen
from .services import ServiceProduksiPanen


class ProduksiPanenListView(LoginRequiredMixin, ListView):
    model = ProduksiPanen
    template_name = "produksi_panen/list.html"
    context_object_name = "data_produksi"


class ProduksiPanenCreateView(LoginRequiredMixin, CreateView):
    model = ProduksiPanen
    form_class = ProduksiPanenForm
    template_name = "produksi_panen/form.html"
    success_url = reverse_lazy("produksi_panen:list")

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            ServiceProduksiPanen.sinkron_produksi(self.object)
        messages.success(self.request, "Data produksi panen berhasil disimpan. Stok persediaan diperbarui.")
        return super().form_valid(form)


class ProduksiPanenUpdateView(LoginRequiredMixin, UpdateView):
    model = ProduksiPanen
    form_class = ProduksiPanenForm
    template_name = "produksi_panen/form.html"
    success_url = reverse_lazy("produksi_panen:list")

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            ServiceProduksiPanen.sinkron_produksi(self.object)
        messages.success(self.request, "Data produksi panen berhasil diperbarui. Stok disinkronkan.")
        return super().form_valid(form)


class ProduksiPanenDeleteView(LoginRequiredMixin, DeleteView):
    model = ProduksiPanen
    success_url = reverse_lazy("produksi_panen:list")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        ServiceProduksiPanen.hapus_dampak_produksi(obj)
        messages.success(request, "Data produksi panen berhasil dihapus. Stok dikembalikan.")
        return super().post(request, *args, **kwargs)
