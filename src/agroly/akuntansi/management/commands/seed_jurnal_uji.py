from decimal import Decimal

from django.core.management.base import BaseCommand

from agroly.akuntansi.models import Akun, JurnalHeader
from agroly.akuntansi.services import BarisJurnal, ServiceJurnal


class Command(BaseCommand):
    help = "Seeder jurnal uji siklus akuntansi AGROLY"

    def handle(self, *args, **options):
        JurnalHeader.objects.filter(sumber_transaksi="seed_uji").delete()

        data = [
            ("1", "Setoran modal awal", "2022-08-01", [("11101", 10000000, 0), ("12401", 5000000, 0), ("11301", 15000000, 0), ("31101", 0, 30000000)]),
            ("2", "Pendapatan penjualan", "2022-08-02", [("11101", 20000000, 0), ("41101", 0, 20000000)]),
            ("4", "Sewa dibayar di muka", "2022-08-04", [("11401", 2200000, 0), ("11101", 0, 2200000)]),
            ("6", "Pembelian peralatan", "2022-08-06", [("12401", 800000, 0), ("11101", 0, 800000)]),
            ("8", "Beban listrik dan air", "2022-08-08", [("61103", 500000, 0), ("11101", 0, 500000)]),
            ("10", "Beban gaji karyawan", "2022-08-10", [("61101", 4000000, 0), ("11101", 0, 4000000)]),
        ]

        for nomor_bukti, keterangan, tanggal, detail in data:
            daftar_baris = []
            for kode_akun, debit, kredit in detail:
                daftar_baris.append(
                    BarisJurnal(
                        akun=Akun.objects.get(kode_akun=kode_akun),
                        debit=Decimal(str(debit)),
                        kredit=Decimal(str(kredit)),
                    )
                )
            ServiceJurnal.posting_jurnal_otomatis(
                tanggal=tanggal,
                nomor_bukti=nomor_bukti,
                keterangan=keterangan,
                sumber_transaksi="seed_uji",
                daftar_baris=daftar_baris,
            )
        self.stdout.write(self.style.SUCCESS("Seeder jurnal uji berhasil dijalankan."))
