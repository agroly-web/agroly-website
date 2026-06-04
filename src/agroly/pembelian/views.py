from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import PembayaranUtangForm, PembelianBarangForm
from .models import PembayaranUtang, PembelianBarang
from .services import ServicePembelian


class PembelianListView(LoginRequiredMixin, ListView):
    model = PembelianBarang
    template_name = "pembelian/list.html"
    context_object_name = "data_pembelian"

    def get_queryset(self):
        return (
            PembelianBarang.objects.select_related("supplier")
            .prefetch_related("detail_pembelian__barang")
            .order_by("-tanggal", "-id")
        )


class PembayaranUtangListView(LoginRequiredMixin, ListView):
    model = PembayaranUtang
    template_name = "pembelian/utang_list.html"
    context_object_name = "data_utang"

    def get_queryset(self):
        return (
            PembayaranUtang.objects.select_related("supplier", "akun_kas_bayar")
            .order_by("-tanggal", "-id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ringkasan_pembelian"] = _ringkasan_pembelian_utang()
        return context


class PembelianCreateView(LoginRequiredMixin, CreateView):
    model = PembelianBarang
    form_class = PembelianBarangForm
    template_name = "pembelian/form.html"
    success_url = reverse_lazy("pembelian:barang")

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.total = 0
            self.object.save()
            ServicePembelian.sinkron_pembelian(
                self.object,
                barang=form.cleaned_data["barang"],
                jumlah=form.cleaned_data["jumlah"],
                harga_satuan=form.cleaned_data["harga_satuan"],
            )
        messages.success(self.request, "Pembelian berhasil disimpan dan jurnal otomatis terbentuk.")
        return super().form_valid(form)


class PembelianUpdateView(LoginRequiredMixin, UpdateView):
    model = PembelianBarang
    form_class = PembelianBarangForm
    template_name = "pembelian/form.html"
    success_url = reverse_lazy("pembelian:barang")

    def get_initial(self):
        initial = super().get_initial()
        detail = self.get_object().detail_pembelian.first()
        if detail:
            initial["barang"] = detail.barang
            initial["jumlah"] = detail.jumlah
            initial["harga_satuan"] = detail.harga_satuan
        return initial

    def form_valid(self, form):
        nomor_lama = self.get_object().nomor_invoice
        with transaction.atomic():
            self.object = form.save()
            ServicePembelian.sinkron_pembelian(
                self.object,
                barang=form.cleaned_data["barang"],
                jumlah=form.cleaned_data["jumlah"],
                harga_satuan=form.cleaned_data["harga_satuan"],
                nomor_invoice_lama=nomor_lama,
            )
        messages.success(self.request, "Pembelian berhasil diperbarui dan jurnal disinkronkan.")
        return super().form_valid(form)


class PembelianDeleteView(LoginRequiredMixin, DeleteView):
    model = PembelianBarang
    success_url = reverse_lazy("pembelian:barang")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        ServicePembelian.hapus_dampak(obj)
        messages.success(request, "Pembelian berhasil dihapus beserta dampak jurnal dan stok.")
        return super().post(request, *args, **kwargs)


def _ringkasan_pembelian_utang():
    return (
        PembelianBarang.objects.filter(status_pembayaran="utang")
        .select_related("supplier")
        .annotate(
            jumlah_bruto=Coalesce(
                Sum("detail_pembelian__subtotal"),
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
        .annotate(total_utang=F("total"))
        .order_by("-tanggal", "-id")
    )


class PembayaranUtangCreateView(LoginRequiredMixin, CreateView):
    model = PembayaranUtang
    form_class = PembayaranUtangForm
    template_name = "pembelian/utang_form.html"
    success_url = reverse_lazy("pembelian:pembayaran_utang")

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            ServicePembelian.sinkron_pembayaran_utang(self.object)
        messages.success(self.request, "Pembayaran utang berhasil disimpan dan jurnal otomatis terbentuk.")
        return super().form_valid(form)


class PembayaranUtangUpdateView(LoginRequiredMixin, UpdateView):
    model = PembayaranUtang
    form_class = PembayaranUtangForm
    template_name = "pembelian/utang_form.html"
    success_url = reverse_lazy("pembelian:pembayaran_utang")

    def form_valid(self, form):
        nomor_lama = self.get_object().nomor_bukti
        with transaction.atomic():
            self.object = form.save()
            ServicePembelian.sinkron_pembayaran_utang(self.object, nomor_bukti_lama=nomor_lama)
        messages.success(self.request, "Pembayaran utang berhasil diperbarui dan jurnal disinkronkan.")
        return super().form_valid(form)


class PembayaranUtangDeleteView(LoginRequiredMixin, DeleteView):
    model = PembayaranUtang
    success_url = reverse_lazy("pembelian:pembayaran_utang")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        ServicePembelian.hapus_dampak_pembayaran_utang(obj)
        messages.success(request, "Pembayaran utang berhasil dihapus beserta dampak jurnal.")
        return super().post(request, *args, **kwargs)
