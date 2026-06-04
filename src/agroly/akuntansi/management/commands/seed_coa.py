from django.core.management.base import BaseCommand

from agroly.akuntansi.models import Akun


DATA_COA = [
    ("11101", "Kas Kecil", "aset"), ("11102", "Kas di Bank", "aset"), ("11201", "Piutang Usaha", "aset"),
    ("11202", "Cadangan Kerugian Piutang", "aset"), ("11301", "Persediaan Barang Dagang", "aset"),
    ("11302", "Perlengkapan Kantor", "aset"), ("11401", "Sewa Dibayar di Muka", "aset"),
    ("11402", "Asuransi Dibayar di Muka", "aset"), ("11403", "Pajak Dibayar di Muka", "aset"),
    ("12101", "Tanah", "aset"), ("12201", "Bangunan", "aset"), ("12202", "Akumulasi Penyusutan Bangunan", "aset"),
    ("12301", "Kendaraan", "aset"), ("12302", "Akumulasi Penyusutan Kendaraan", "aset"),
    ("12401", "Peralatan Kantor", "aset"), ("12402", "Akumulasi Penyusutan Peralatan Kantor", "aset"),
    ("21101", "Utang Usaha", "kewajiban"), ("21201", "Utang Gaji dan Upah", "kewajiban"),
    ("31101", "Modal Pemilik", "ekuitas"), ("31201", "Prive Pemilik", "ekuitas"),
    ("31301", "Laba Ditahan", "ekuitas"), ("31401", "Ikhtisar Laba Rugi", "ekuitas"),
    ("41101", "Pendapatan Penjualan", "pendapatan"), ("41102", "Retur Penjualan", "pendapatan"),
    ("41103", "Potongan Penjualan", "pendapatan"), ("51101", "Harga Pokok Penjualan", "hpp"),
    ("51201", "Pembelian Barang Dagang", "hpp"), ("51202", "Beban Angkut Pembelian", "hpp"),
    ("51203", "Retur Pembelian", "hpp"), ("51204", "Potongan Pembelian", "hpp"),
    ("61101", "Beban Gaji dan Komisi", "beban_operasional"), ("61102", "Beban Sewa Bangunan", "beban_operasional"),
    ("61103", "Beban Listrik Air dan Telepon", "beban_operasional"),
    ("61104", "Beban Perlengkapan Kantor", "beban_operasional"),
    ("61105", "Beban Iklan dan Pemasaran", "beban_operasional"),
    ("61106", "Beban Penyusutan Bangunan", "beban_operasional"),
    ("61107", "Beban Penyusutan Kendaraan", "beban_operasional"),
    ("61108", "Beban Penyusutan Peralatan", "beban_operasional"), ("61109", "Beban Asuransi", "beban_operasional"),
    ("61110", "Beban Kerugian Piutang", "beban_operasional"), ("81101", "Pendapatan Bunga Bank", "pendapatan_lain"),
    ("81102", "Keuntungan Penjualan Aset Tetap", "pendapatan_lain"), ("91101", "Beban Bunga Bank", "beban_lain"),
    ("91102", "Beban Administrasi Bank", "beban_lain"), ("91104", "Beban Pajak Penghasilan", "beban_lain"),
]


class Command(BaseCommand):
    help = "Seeder data awal daftar akun AGROLY"

    def handle(self, *args, **options):
        for kode, nama, kategori in DATA_COA:
            Akun.objects.update_or_create(
                kode_akun=kode,
                defaults={"nama_akun": nama, "kategori_akun": kategori, "aktif": True},
            )
        self.stdout.write(self.style.SUCCESS("Seeder COA berhasil dijalankan."))
