from decimal import Decimal
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, TemplateView

from .forms import (
    AkunForm,
    JurnalDetailFormSet,
    JurnalHeaderForm,
    JurnalPenyesuaianDetailFormSet,
    JurnalPenyesuaianHeaderForm,
)
from .models import Akun, JurnalDetail, JurnalHeader
from .services import BarisJurnal, ServiceJurnal, ServiceLaporanKeuangan

SUMBER_PENYESUAIAN = "penyesuaian"


def _akun_nama_map() -> dict[str, str]:
    return {str(akun.pk): akun.nama_akun for akun in Akun.objects.filter(aktif=True)}


def _baris_penyesuaian_dari_formset(form_detail) -> list[BarisJurnal]:
    daftar = []
    for form in form_detail:
        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
            continue
        akun = form.cleaned_data.get("akun")
        if not akun:
            continue
        daftar.append(
            BarisJurnal(
                akun=akun,
                debit=form.cleaned_data.get("debit") or Decimal("0"),
                kredit=form.cleaned_data.get("kredit") or Decimal("0"),
            )
        )
    return daftar


def _validasi_balance_formset(form_detail) -> tuple[Decimal, Decimal, int] | None:
    total_debit = Decimal("0")
    total_kredit = Decimal("0")
    baris_valid = 0
    for form in form_detail:
        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
            continue
        if not form.cleaned_data.get("akun"):
            continue
        total_debit += form.cleaned_data.get("debit") or Decimal("0")
        total_kredit += form.cleaned_data.get("kredit") or Decimal("0")
        baris_valid += 1
    if baris_valid < 2:
        return None
    if total_debit != total_kredit:
        return None
    return total_debit, total_kredit, baris_valid


def _bangun_baris_penyesuaian_list(daftar_jurnal):
    total_debit = Decimal("0")
    total_kredit = Decimal("0")
    baris_jurnal = []
    for header in daftar_jurnal:
        detail_header = list(header.detail_jurnal.all())
        for idx, detail in enumerate(detail_header):
            total_debit += detail.debit
            total_kredit += detail.kredit
            baris_jurnal.append(
                {
                    "tanggal": header.tanggal if idx == 0 else "",
                    "nomor_bukti": header.nomor_bukti if idx == 0 else "",
                    "keterangan": header.keterangan if idx == 0 else "",
                    "kode_akun": detail.akun.kode_akun,
                    "nama_akun": detail.akun.nama_akun,
                    "debit": detail.debit,
                    "kredit": detail.kredit,
                    "header_id": header.pk if idx == 0 else None,
                }
            )
    return baris_jurnal, total_debit, total_kredit


class AkunListView(LoginRequiredMixin, ListView):
    model = Akun
    template_name = "akuntansi/akun_list.html"
    context_object_name = "daftar_akun"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["daftar_akun"] = [
            {"akun": akun, **ServiceLaporanKeuangan.balance_akun_untuk_daftar(akun)}
            for akun in context["daftar_akun"]
        ]
        return context


class AkunCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "akuntansi/akun_form.html", {"form": AkunForm()})

    def post(self, request):
        form = AkunForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Akun berhasil disimpan.")
            return redirect("akuntansi:daftar_akun")
        return render(request, "akuntansi/akun_form.html", {"form": form})


class AkunUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        akun = get_object_or_404(Akun, pk=pk)
        form = AkunForm(instance=akun)
        return render(request, "akuntansi/akun_form.html", {"form": form, "mode": "edit"})

    def post(self, request, pk):
        akun = get_object_or_404(Akun, pk=pk)
        form = AkunForm(request.POST, instance=akun)
        if form.is_valid():
            form.save()
            messages.success(request, "Akun berhasil diperbarui.")
            return redirect("akuntansi:daftar_akun")
        return render(request, "akuntansi/akun_form.html", {"form": form, "mode": "edit"})


class AkunDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        akun = get_object_or_404(Akun, pk=pk)
        akun.delete()
        messages.success(request, "Akun berhasil dihapus.")
        return redirect("akuntansi:daftar_akun")


class JurnalListView(LoginRequiredMixin, ListView):
    model = JurnalHeader
    template_name = "akuntansi/jurnal_list.html"
    context_object_name = "daftar_jurnal"

    def get_queryset(self):
        queryset = (
            JurnalHeader.objects.exclude(sumber_transaksi=SUMBER_PENYESUAIAN)
            .prefetch_related("detail_jurnal__akun")
            .order_by("tanggal", "nomor_bukti", "id")
        )
        bulan = self.request.GET.get("bulan")
        if bulan:
            try:
                parsed = datetime.strptime(bulan, "%Y-%m")
                queryset = queryset.filter(tanggal__year=parsed.year, tanggal__month=parsed.month)
            except ValueError:
                messages.error(self.request, "Format bulan tidak valid. Gunakan YYYY-MM.")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bulan_aktif"] = self.request.GET.get("bulan", "")
        total_debit = Decimal("0")
        total_kredit = Decimal("0")
        baris_jurnal = []
        for header in context["daftar_jurnal"]:
            detail_header = list(header.detail_jurnal.all())
            for idx, detail in enumerate(detail_header):
                total_debit += detail.debit
                total_kredit += detail.kredit
                baris_jurnal.append(
                    {
                        "tanggal": header.tanggal if idx == 0 else "",
                        "nomor_bukti": header.nomor_bukti if idx == 0 else "",
                        "nama_akun": detail.akun.nama_akun,
                        "keterangan": header.keterangan if idx == 0 else "",
                        "ref": detail.akun.kode_akun[:3],
                        "debit": detail.debit,
                        "kredit": detail.kredit,
                        "header_id": header.pk if idx == 0 else None,
                    }
                )
        context["baris_jurnal"] = baris_jurnal
        context["total_debit"] = total_debit
        context["total_kredit"] = total_kredit
        jurnal_pertama = context["daftar_jurnal"].first()
        context["periode_label"] = jurnal_pertama.tanggal.strftime("%B %Y") if jurnal_pertama else ""
        return context


class JurnalCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form_header = JurnalHeaderForm()
        form_detail = JurnalDetailFormSet()
        return render(
            request,
            "akuntansi/jurnal_form.html",
            {"form_header": form_header, "form_detail": form_detail},
        )

    def post(self, request):
        form_header = JurnalHeaderForm(request.POST)
        form_detail = JurnalDetailFormSet(request.POST)
        if form_header.is_valid() and form_detail.is_valid():
            total_debit = Decimal("0")
            total_kredit = Decimal("0")
            baris_valid = 0
            for form in form_detail:
                if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                    continue
                if not form.cleaned_data.get("akun"):
                    continue
                posisi = form.cleaned_data.get("posisi")
                nominal = form.cleaned_data.get("nominal", Decimal("0"))
                if posisi == "debit":
                    total_debit += nominal
                else:
                    total_kredit += nominal
                baris_valid += 1
            if baris_valid < 2:
                messages.error(request, "Jurnal harus memiliki minimal dua baris detail.")
                return render(
                    request,
                    "akuntansi/jurnal_form.html",
                    {"form_header": form_header, "form_detail": form_detail},
                )
            if total_debit != total_kredit:
                messages.error(request, "Jurnal tidak balance. Total debit harus sama dengan total kredit.")
                return render(
                    request,
                    "akuntansi/jurnal_form.html",
                    {"form_header": form_header, "form_detail": form_detail},
                )
            with transaction.atomic():
                header = form_header.save(commit=False)
                header.sumber_transaksi = "manual"
                header.save()
                form_detail.instance = header
                form_detail.save()
            messages.success(request, "Jurnal berhasil disimpan.")
            return redirect("akuntansi:daftar_jurnal")
        return render(
            request,
            "akuntansi/jurnal_form.html",
            {"form_header": form_header, "form_detail": form_detail},
        )


class JurnalUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        header = get_object_or_404(JurnalHeader, pk=pk)
        if header.sumber_transaksi == SUMBER_PENYESUAIAN:
            messages.error(request, "Gunakan menu Jurnal Penyesuaian untuk mengedit entri ini.")
            return redirect("akuntansi:daftar_penyesuaian")
        form_header = JurnalHeaderForm(instance=header)
        form_detail = JurnalDetailFormSet(instance=header)
        return render(
            request,
            "akuntansi/jurnal_form.html",
            {"form_header": form_header, "form_detail": form_detail, "mode": "edit"},
        )

    def post(self, request, pk):
        header = get_object_or_404(JurnalHeader, pk=pk)
        if header.sumber_transaksi == SUMBER_PENYESUAIAN:
            messages.error(request, "Gunakan menu Jurnal Penyesuaian untuk mengedit entri ini.")
            return redirect("akuntansi:daftar_penyesuaian")
        form_header = JurnalHeaderForm(request.POST, instance=header)
        form_detail = JurnalDetailFormSet(request.POST, instance=header)
        if form_header.is_valid() and form_detail.is_valid():
            total_debit = Decimal("0")
            total_kredit = Decimal("0")
            baris_valid = 0
            for form in form_detail:
                if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                    continue
                if not form.cleaned_data.get("akun"):
                    continue
                posisi = form.cleaned_data.get("posisi")
                nominal = form.cleaned_data.get("nominal", Decimal("0"))
                if posisi == "debit":
                    total_debit += nominal
                else:
                    total_kredit += nominal
                baris_valid += 1
            if baris_valid < 2:
                messages.error(request, "Jurnal harus memiliki minimal dua baris detail.")
                return render(
                    request,
                    "akuntansi/jurnal_form.html",
                    {"form_header": form_header, "form_detail": form_detail, "mode": "edit"},
                )
            if total_debit != total_kredit:
                messages.error(request, "Jurnal tidak balance. Total debit harus sama dengan total kredit.")
                return render(
                    request,
                    "akuntansi/jurnal_form.html",
                    {"form_header": form_header, "form_detail": form_detail, "mode": "edit"},
                )
            with transaction.atomic():
                jurnal = form_header.save(commit=False)
                jurnal.sumber_transaksi = "manual"
                jurnal.save()
                form_detail.save()
            messages.success(request, "Jurnal berhasil diperbarui.")
            return redirect("akuntansi:daftar_jurnal")
        return render(
            request,
            "akuntansi/jurnal_form.html",
            {"form_header": form_header, "form_detail": form_detail, "mode": "edit"},
        )


class JurnalDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        header = get_object_or_404(JurnalHeader, pk=pk)
        if header.sumber_transaksi == SUMBER_PENYESUAIAN:
            messages.error(request, "Gunakan menu Jurnal Penyesuaian untuk menghapus entri ini.")
            return redirect("akuntansi:daftar_penyesuaian")
        header.delete()
        messages.success(request, "Jurnal berhasil dihapus.")
        return redirect("akuntansi:daftar_jurnal")


class JurnalPenyesuaianListView(LoginRequiredMixin, ListView):
    model = JurnalHeader
    template_name = "akuntansi/penyesuaian_list.html"
    context_object_name = "daftar_penyesuaian"

    def get_queryset(self):
        queryset = (
            JurnalHeader.objects.filter(sumber_transaksi=SUMBER_PENYESUAIAN)
            .prefetch_related("detail_jurnal__akun")
            .order_by("tanggal", "nomor_bukti", "id")
        )
        bulan = self.request.GET.get("bulan")
        if bulan:
            try:
                parsed = datetime.strptime(bulan, "%Y-%m")
                queryset = queryset.filter(tanggal__year=parsed.year, tanggal__month=parsed.month)
            except ValueError:
                messages.error(self.request, "Format bulan tidak valid. Gunakan YYYY-MM.")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bulan_aktif"] = self.request.GET.get("bulan", "")
        baris, total_debit, total_kredit = _bangun_baris_penyesuaian_list(context["daftar_penyesuaian"])
        context["baris_jurnal"] = baris
        context["total_debit"] = total_debit
        context["total_kredit"] = total_kredit
        pertama = context["daftar_penyesuaian"].first()
        context["periode_label"] = pertama.tanggal.strftime("%B %Y") if pertama else ""
        return context


class JurnalPenyesuaianCreateView(LoginRequiredMixin, View):
    def _render(self, request, form_header, form_detail, mode=None):
        return render(
            request,
            "akuntansi/penyesuaian_form.html",
            {
                "form_header": form_header,
                "form_detail": form_detail,
                "akun_nama_map": _akun_nama_map(),
                "mode": mode,
            },
        )

    def get(self, request):
        return self._render(
            request,
            JurnalPenyesuaianHeaderForm(),
            JurnalPenyesuaianDetailFormSet(),
        )

    def post(self, request):
        form_header = JurnalPenyesuaianHeaderForm(request.POST)
        form_detail = JurnalPenyesuaianDetailFormSet(request.POST)
        if form_header.is_valid() and form_detail.is_valid():
            if _validasi_balance_formset(form_detail) is None:
                messages.error(
                    request,
                    "Jurnal penyesuaian tidak valid. Minimal dua baris dan total debit = total kredit.",
                )
                return self._render(request, form_header, form_detail)
            with transaction.atomic():
                header = form_header.save(commit=False)
                if not header.nomor_bukti:
                    header.nomor_bukti = ServiceJurnal.nomor_penyesuaian_baru(header.tanggal)
                header.sumber_transaksi = SUMBER_PENYESUAIAN
                header.save()
                ServiceJurnal.ganti_isi_jurnal(
                    header, _baris_penyesuaian_dari_formset(form_detail)
                )
            messages.success(request, "Jurnal penyesuaian berhasil disimpan.")
            return redirect("akuntansi:daftar_penyesuaian")
        return self._render(request, form_header, form_detail)


class JurnalPenyesuaianUpdateView(LoginRequiredMixin, View):
    def _render(self, request, form_header, form_detail):
        return render(
            request,
            "akuntansi/penyesuaian_form.html",
            {
                "form_header": form_header,
                "form_detail": form_detail,
                "akun_nama_map": _akun_nama_map(),
                "mode": "edit",
            },
        )

    def get(self, request, pk):
        header = get_object_or_404(JurnalHeader, pk=pk, sumber_transaksi=SUMBER_PENYESUAIAN)
        return self._render(
            request,
            JurnalPenyesuaianHeaderForm(instance=header),
            JurnalPenyesuaianDetailFormSet(instance=header),
        )

    def post(self, request, pk):
        header = get_object_or_404(JurnalHeader, pk=pk, sumber_transaksi=SUMBER_PENYESUAIAN)
        form_header = JurnalPenyesuaianHeaderForm(request.POST, instance=header)
        form_detail = JurnalPenyesuaianDetailFormSet(request.POST, instance=header)
        if form_header.is_valid() and form_detail.is_valid():
            if _validasi_balance_formset(form_detail) is None:
                messages.error(
                    request,
                    "Jurnal penyesuaian tidak valid. Minimal dua baris dan total debit = total kredit.",
                )
                return self._render(request, form_header, form_detail)
            with transaction.atomic():
                jurnal = form_header.save(commit=False)
                if not jurnal.nomor_bukti:
                    jurnal.nomor_bukti = ServiceJurnal.nomor_penyesuaian_baru(jurnal.tanggal)
                jurnal.sumber_transaksi = SUMBER_PENYESUAIAN
                jurnal.save()
                ServiceJurnal.ganti_isi_jurnal(
                    jurnal, _baris_penyesuaian_dari_formset(form_detail)
                )
            messages.success(request, "Jurnal penyesuaian berhasil diperbarui.")
            return redirect("akuntansi:daftar_penyesuaian")
        return self._render(request, form_header, form_detail)


class JurnalPenyesuaianDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        header = get_object_or_404(JurnalHeader, pk=pk, sumber_transaksi=SUMBER_PENYESUAIAN)
        header.delete()
        messages.success(request, "Jurnal penyesuaian berhasil dihapus.")
        return redirect("akuntansi:daftar_penyesuaian")


class LaporanLabaRugiView(LoginRequiredMixin, TemplateView):
    template_name = "akuntansi/laporan_laba_rugi.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["laba_rugi_detail"] = ServiceLaporanKeuangan.hitung_laba_rugi_terstruktur()
        return context


class LaporanNeracaView(LoginRequiredMixin, TemplateView):
    template_name = "akuntansi/laporan_neraca.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["neraca_detail"] = ServiceLaporanKeuangan.hitung_neraca_terstruktur()
        return context


class LaporanArusKasView(LoginRequiredMixin, TemplateView):
    template_name = "akuntansi/laporan_arus_kas.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["arus_kas_detail"] = ServiceLaporanKeuangan.hitung_arus_kas_terstruktur()
        return context
