from copy import deepcopy

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import BarangPersediaanForm, MutasiPersediaanForm
from .models import BarangPersediaan, MutasiPersediaan
from .services import ServicePersediaan


class BarangListView(LoginRequiredMixin, ListView):
    model = BarangPersediaan
    template_name = "persediaan/barang_list.html"
    context_object_name = "daftar_barang"


class MutasiPersediaanListView(LoginRequiredMixin, ListView):
    model = MutasiPersediaan
    template_name = "persediaan/mutasi_list.html"
    context_object_name = "riwayat_mutasi"


class BarangCreateView(LoginRequiredMixin, CreateView):
    model = BarangPersediaan
    form_class = BarangPersediaanForm
    template_name = "persediaan/barang_form.html"
    success_url = reverse_lazy("persediaan:barang")


class BarangUpdateView(LoginRequiredMixin, UpdateView):
    model = BarangPersediaan
    form_class = BarangPersediaanForm
    template_name = "persediaan/barang_form.html"
    success_url = reverse_lazy("persediaan:barang")


class BarangDeleteView(LoginRequiredMixin, DeleteView):
    model = BarangPersediaan
    success_url = reverse_lazy("persediaan:barang")


class MutasiCreateView(LoginRequiredMixin, CreateView):
    model = MutasiPersediaan
    form_class = MutasiPersediaanForm
    template_name = "persediaan/mutasi_form.html"
    success_url = reverse_lazy("persediaan:penyesuaian")

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            ServicePersediaan.sinkron_mutasi(self.object)
        messages.success(self.request, "Mutasi persediaan berhasil disimpan. Stok diperbarui.")
        return super().form_valid(form)


class MutasiUpdateView(LoginRequiredMixin, UpdateView):
    model = MutasiPersediaan
    form_class = MutasiPersediaanForm
    template_name = "persediaan/mutasi_form.html"
    success_url = reverse_lazy("persediaan:penyesuaian")

    def form_valid(self, form):
        mutasi_lama = deepcopy(self.get_object())
        with transaction.atomic():
            self.object = form.save()
            ServicePersediaan.sinkron_mutasi(self.object, mutasi_lama)
        messages.success(self.request, "Mutasi persediaan berhasil diperbarui. Stok disinkronkan.")
        return super().form_valid(form)


class MutasiDeleteView(LoginRequiredMixin, DeleteView):
    model = MutasiPersediaan
    success_url = reverse_lazy("persediaan:penyesuaian")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        ServicePersediaan.hapus_dampak_mutasi(obj)
        messages.success(request, "Mutasi persediaan berhasil dihapus. Stok dikembalikan.")
        return super().post(request, *args, **kwargs)
