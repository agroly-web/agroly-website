from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import PenerimaanPiutangForm, PenjualanBarangForm
from .models import PenerimaanPiutang, PenjualanBarang
from .services import ServicePenjualan


class PenjualanListView(LoginRequiredMixin, ListView):
    model = PenjualanBarang
    template_name = "penjualan/list.html"
    context_object_name = "data_penjualan"

    def get_queryset(self):
        return (
            PenjualanBarang.objects.select_related("customer")
            .prefetch_related("detail_penjualan__barang")
            .order_by("-tanggal", "-id")
        )


class PenerimaanPiutangListView(LoginRequiredMixin, ListView):
    model = PenerimaanPiutang
    template_name = "penjualan/piutang_list.html"
    context_object_name = "data_piutang"

    def get_queryset(self):
        return (
            PenerimaanPiutang.objects.select_related("customer", "akun_kas_setoran")
            .order_by("-tanggal", "-id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ringkasan_penjualan"] = _ringkasan_penjualan_piutang()
        return context


class PenjualanCreateView(LoginRequiredMixin, CreateView):
    model = PenjualanBarang
    form_class = PenjualanBarangForm
    template_name = "penjualan/form.html"
    success_url = reverse_lazy("penjualan:barang")

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.total = 0
            self.object.save()
            ServicePenjualan.sinkron_penjualan(
                self.object,
                barang=form.cleaned_data["barang"],
                jumlah=form.cleaned_data["jumlah"],
                harga_satuan=form.cleaned_data["harga_satuan"],
            )
        messages.success(self.request, "Penjualan berhasil disimpan dan jurnal otomatis terbentuk.")
        return super().form_valid(form)


class PenjualanUpdateView(LoginRequiredMixin, UpdateView):
    model = PenjualanBarang
    form_class = PenjualanBarangForm
    template_name = "penjualan/form.html"
    success_url = reverse_lazy("penjualan:barang")

    def get_initial(self):
        initial = super().get_initial()
        detail = self.get_object().detail_penjualan.first()
        if detail:
            initial["barang"] = detail.barang
            initial["jumlah"] = detail.jumlah
            initial["harga_satuan"] = detail.harga_satuan
        return initial

    def form_valid(self, form):
        nomor_lama = self.get_object().nomor_invoice
        with transaction.atomic():
            self.object = form.save()
            ServicePenjualan.sinkron_penjualan(
                self.object,
                barang=form.cleaned_data["barang"],
                jumlah=form.cleaned_data["jumlah"],
                harga_satuan=form.cleaned_data["harga_satuan"],
                nomor_invoice_lama=nomor_lama,
            )
        messages.success(self.request, "Penjualan berhasil diperbarui dan jurnal disinkronkan.")
        return super().form_valid(form)


class PenjualanDeleteView(LoginRequiredMixin, DeleteView):
    model = PenjualanBarang
    success_url = reverse_lazy("penjualan:barang")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        ServicePenjualan.hapus_dampak(obj)
        messages.success(request, "Penjualan berhasil dihapus beserta dampak jurnal dan stok.")
        return super().post(request, *args, **kwargs)


def _ringkasan_penjualan_piutang():
    return (
        PenjualanBarang.objects.filter(status_pembayaran="piutang")
        .select_related("customer")
        .annotate(
            jumlah_bruto=Coalesce(
                Sum("detail_penjualan__subtotal"),
                Value(0),
                output_field=DecimalField(max_digits=18, decimal_places=2),
            )
        )
        .annotate(
            diskon_nilai=ExpressionWrapper(
                F("jumlah_bruto") * F("diskon_persen") / Value(100),
                output_field=DecimalField(max_digits=18, decimal_places=2),
            )
        )
        .annotate(total_piutang=F("total"))
        .order_by("-tanggal", "-id")
    )


class PenerimaanPiutangCreateView(LoginRequiredMixin, CreateView):
    model = PenerimaanPiutang
    form_class = PenerimaanPiutangForm
    template_name = "penjualan/piutang_form.html"
    success_url = reverse_lazy("penjualan:penerimaan_piutang")

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            ServicePenjualan.sinkron_penerimaan_piutang(self.object)
        messages.success(self.request, "Penerimaan piutang berhasil disimpan dan jurnal otomatis terbentuk.")
        return super().form_valid(form)


class PenerimaanPiutangUpdateView(LoginRequiredMixin, UpdateView):
    model = PenerimaanPiutang
    form_class = PenerimaanPiutangForm
    template_name = "penjualan/piutang_form.html"
    success_url = reverse_lazy("penjualan:penerimaan_piutang")

    def form_valid(self, form):
        nomor_lama = self.get_object().nomor_bukti
        with transaction.atomic():
            self.object = form.save()
            ServicePenjualan.sinkron_penerimaan_piutang(self.object, nomor_bukti_lama=nomor_lama)
        messages.success(self.request, "Penerimaan piutang berhasil diperbarui dan jurnal disinkronkan.")
        return super().form_valid(form)


class PenerimaanPiutangDeleteView(LoginRequiredMixin, DeleteView):
    model = PenerimaanPiutang
    success_url = reverse_lazy("penjualan:penerimaan_piutang")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        ServicePenjualan.hapus_dampak_penerimaan_piutang(obj)
        messages.success(request, "Penerimaan piutang berhasil dihapus beserta dampak jurnal.")
        return super().post(request, *args, **kwargs)
