from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.views.generic import TemplateView

from agroly.pembelian.models import PembelianBarang
from agroly.penjualan.models import PenjualanBarang
from agroly.produksi_panen.models import ProduksiPanen


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/beranda.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_produksi = ProduksiPanen.objects.aggregate(total=Sum("jumlah_hasil_panen"))["total"] or 0
        total_pendapatan = PenjualanBarang.objects.aggregate(total=Sum("total"))["total"] or 0
        total_pengeluaran = PembelianBarang.objects.aggregate(total=Sum("total"))["total"] or 0
        context.update(
            {
                "total_produksi": total_produksi,
                "total_pendapatan": total_pendapatan,
                "total_pengeluaran": total_pengeluaran,
                "laba_bersih": total_pendapatan - total_pengeluaran,
            }
        )
        return context
