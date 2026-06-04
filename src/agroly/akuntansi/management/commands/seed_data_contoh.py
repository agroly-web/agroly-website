from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from agroly.akuntansi.models import Akun, JurnalHeader
from agroly.pembelian.models import PembayaranUtang, PembelianBarang
from agroly.pembelian.services import ServicePembelian
from agroly.penjualan.models import PenerimaanPiutang, PenjualanBarang
from agroly.penjualan.services import ServicePenjualan
from agroly.persediaan.models import BarangPersediaan, MutasiPersediaan
from agroly.persediaan.services import ServicePersediaan
from agroly.produksi_panen.models import ProduksiPanen
from agroly.produksi_panen.services import ServiceProduksiPanen
from agroly.relasi_bisnis.models import Customer, Supplier


DATA_BARANG = [
    ("BRG-001", "Kelengkeng Super A (Crystal)", Decimal("100"), "kg", Decimal("45000"), Decimal("70000")),
    ("BRG-002", "Kelengkeng Itoh", Decimal("80"), "kg", Decimal("42000"), Decimal("65000")),
    ("BRG-003", "Kelengkeng Diamond", Decimal("60"), "kg", Decimal("48000"), Decimal("72000")),
    ("BRG-004", "Kelengkeng Bangkok", Decimal("60"), "kg", Decimal("40000"), Decimal("62000")),
    ("BRG-005", "Pupuk NPK Kelengkeng", Decimal("200"), "kg", Decimal("25000"), Decimal("32000")),
    ("BRG-006", "Kemasan Plastik 1kg", Decimal("500"), "pcs", Decimal("3500"), Decimal("5000")),
]


class Command(BaseCommand):
    help = "Seeder data contoh lengkap semua fitur AGROLY (jurnal & stok otomatis via service)"

    def handle(self, *args, **options):
        akun_kas_bank = Akun.objects.filter(kode_akun="11102").first()
        if not akun_kas_bank:
            self.stderr.write(self.style.ERROR("Akun COA belum ada. Jalankan seed_coa terlebih dahulu."))
            return

        with transaction.atomic():
            customer1 = self._pelanggan("Toko Bu Ani", "C-01", "CUST-001", "Bandung", "08120000111")
            customer2 = self._pelanggan("Pasar Segar Jaya", "C-02", "CUST-002", "Garut", "08120000222")
            customer3 = self._pelanggan("Retail Kelengkeng ABC", "C-03", "CUST-003", "Cimahi", "08120000333")

            supplier1 = self._pemasok("PT Pupuk Nusantara", "S-01", "SUP-001", "Jakarta", "08130000111")
            supplier2 = self._pemasok("CV Alat Tani Maju", "S-02", "SUP-002", "Bogor", "08130000222")

            barang = {}
            for kode, nama, stok, satuan, beli, jual in DATA_BARANG:
                barang[kode], _ = BarangPersediaan.objects.get_or_create(
                    kode_barang=kode,
                    defaults={
                        "nama_barang": nama,
                        "stok": stok,
                        "satuan": satuan,
                        "harga_beli": beli,
                        "harga_jual": jual,
                        "aktif": True,
                    },
                )

            self._sinkron_produksi("2022-08-05", "Kelengkeng Super A (Crystal)", "A", Decimal("125"), "Panen blok A")
            self._sinkron_produksi("2022-08-07", "Kelengkeng Itoh", "B", Decimal("95"), "Panen blok B")
            self._sinkron_produksi("2022-08-09", "Kelengkeng Diamond", "A", Decimal("80"), "Panen blok C")
            self._sinkron_produksi("2022-08-11", "Kelengkeng Bangkok", "B", Decimal("70"), "Panen blok D")

            self._sinkron_mutasi(
                "MUT-001", "2022-08-13", barang["BRG-002"], "keluar", Decimal("15"),
                "Sampel mutasi keluar ke produksi olahan",
            )
            self._sinkron_mutasi(
                "MUT-002", "2022-08-14", barang["BRG-005"], "masuk", Decimal("50"),
                "Sampel mutasi masuk stok pupuk",
            )

            self._sinkron_pembelian(
                "INV-BELI-001",
                {
                    "tanggal": "2022-08-15",
                    "supplier": supplier1,
                    "nomor_faktur_pemasok": "FP-001",
                    "termin_pembayaran": "2/10 n/30",
                    "diskon_persen": Decimal("1"),
                    "pajak_persen": Decimal("11"),
                    "status_pembayaran": "utang",
                    "keterangan": "Case A: pembelian pupuk (Piutang)",
                },
                barang["BRG-005"],
                Decimal("100"),
                Decimal("25000"),
            )
            self._sinkron_pembelian(
                "INV-BELI-002",
                {
                    "tanggal": "2022-08-16",
                    "supplier": supplier1,
                    "nomor_faktur_pemasok": "FP-002",
                    "termin_pembayaran": "2/10 n/30",
                    "diskon_persen": Decimal("0"),
                    "pajak_persen": Decimal("11"),
                    "status_pembayaran": "utang",
                    "keterangan": "Case B: pembelian kemasan (Piutang)",
                },
                barang["BRG-006"],
                Decimal("200"),
                Decimal("3500"),
            )
            self._sinkron_pembelian(
                "INV-BELI-003",
                {
                    "tanggal": "2022-08-17",
                    "supplier": supplier2,
                    "nomor_faktur_pemasok": "FP-003",
                    "termin_pembayaran": "Cash",
                    "diskon_persen": Decimal("2"),
                    "pajak_persen": Decimal("11"),
                    "status_pembayaran": "tunai",
                    "keterangan": "Case C: pembelian alat kemas (Tunai)",
                },
                barang["BRG-006"],
                Decimal("100"),
                Decimal("3200"),
            )

            self._sinkron_penjualan(
                "INV-JUAL-001",
                {
                    "tanggal": "2022-08-18",
                    "customer": customer2,
                    "termin_pembayaran": "2/10 n/30",
                    "diskon_persen": Decimal("2"),
                    "pajak_persen": Decimal("11"),
                    "status_pembayaran": "piutang",
                    "keterangan": "Case A: penjualan ke pasar (Piutang)",
                },
                barang["BRG-001"],
                Decimal("40"),
                Decimal("70000"),
            )
            self._sinkron_penjualan(
                "INV-JUAL-002",
                {
                    "tanggal": "2022-08-19",
                    "customer": customer3,
                    "termin_pembayaran": "2/10 n/30",
                    "diskon_persen": Decimal("1"),
                    "pajak_persen": Decimal("11"),
                    "status_pembayaran": "piutang",
                    "keterangan": "Case B: penjualan retail ABC (Piutang)",
                },
                barang["BRG-003"],
                Decimal("25"),
                Decimal("72000"),
            )
            self._sinkron_penjualan(
                "INV-JUAL-003",
                {
                    "tanggal": "2022-08-20",
                    "customer": customer1,
                    "termin_pembayaran": "Cash",
                    "diskon_persen": Decimal("0"),
                    "pajak_persen": Decimal("11"),
                    "status_pembayaran": "tunai",
                    "keterangan": "Case C: penjualan toko Bu Ani (Tunai)",
                },
                barang["BRG-001"],
                Decimal("20"),
                Decimal("70000"),
            )
            self._sinkron_penjualan(
                "INV-JUAL-004",
                {
                    "tanggal": "2022-08-21",
                    "customer": customer1,
                    "termin_pembayaran": "Cash",
                    "diskon_persen": Decimal("0"),
                    "pajak_persen": Decimal("11"),
                    "status_pembayaran": "tunai",
                    "keterangan": "Case D: penjualan Bangkok grade B (Tunai)",
                },
                barang["BRG-004"],
                Decimal("15"),
                Decimal("62000"),
            )

            self._sinkron_penerimaan(
                "TERIMA-001",
                {
                    "tanggal": "2022-08-22",
                    "akun_kas_setoran": akun_kas_bank,
                    "customer": customer2,
                    "faktur_no": "INV-JUAL-001",
                    "jumlah_terima": Decimal("2500000"),
                    "diskon": Decimal("50000"),
                    "keterangan": "Pelunasan sebagian piutang Pasar Segar Jaya",
                },
            )
            self._sinkron_penerimaan(
                "TERIMA-002",
                {
                    "tanggal": "2022-08-23",
                    "akun_kas_setoran": akun_kas_bank,
                    "customer": customer3,
                    "faktur_no": "INV-JUAL-002",
                    "jumlah_terima": Decimal("1500000"),
                    "diskon": Decimal("0"),
                    "keterangan": "Pelunasan sebagian piutang Retail Kelengkeng ABC",
                },
            )

            self._sinkron_pembayaran_utang(
                "BAYAR-001",
                {
                    "tanggal": "2022-08-24",
                    "akun_kas_bayar": akun_kas_bank,
                    "supplier": supplier1,
                    "no_cek": "CHK-001",
                    "jumlah_bayar": Decimal("2000000"),
                    "diskon": Decimal("0"),
                    "keterangan": "Pelunasan sebagian piutang PT Pupuk Nusantara",
                },
            )
            self._sinkron_pembayaran_utang(
                "BAYAR-002",
                {
                    "tanggal": "2022-08-25",
                    "akun_kas_bayar": akun_kas_bank,
                    "supplier": supplier1,
                    "no_cek": "CHK-002",
                    "jumlah_bayar": Decimal("500000"),
                    "diskon": Decimal("25000"),
                    "keterangan": "Pelunasan tambahan piutang PT Pupuk Nusantara",
                },
            )

        self.stdout.write(self.style.SUCCESS("Seeder data contoh lengkap berhasil dijalankan."))
        self._cetak_ringkasan()

    def _pelanggan(self, nama, numbering, no_kartu, alamat, telepon):
        obj, _ = Customer.objects.update_or_create(
            numbering=numbering,
            defaults={
                "nama": nama,
                "no_kartu": no_kartu,
                "alamat": alamat,
                "telepon": telepon,
                "saldo_saat_ini": Decimal("0"),
                "aktif": True,
            },
        )
        return obj

    def _pemasok(self, nama, numbering, no_kartu, alamat, telepon):
        obj, _ = Supplier.objects.update_or_create(
            numbering=numbering,
            defaults={
                "nama": nama,
                "no_kartu": no_kartu,
                "alamat": alamat,
                "telepon": telepon,
                "saldo_saat_ini": Decimal("0"),
                "aktif": True,
            },
        )
        return obj

    def _sudah_jurnal(self, nomor_bukti):
        return JurnalHeader.objects.filter(nomor_bukti=nomor_bukti).exists()

    def _sinkron_produksi(self, tanggal, komoditas, grade, jumlah, keterangan):
        produksi, created = ProduksiPanen.objects.get_or_create(
            tanggal=tanggal,
            komoditas=komoditas,
            grade=grade,
            defaults={
                "jumlah_hasil_panen": jumlah,
                "satuan": "kg",
                "keterangan": keterangan,
            },
        )
        if created or not self._sudah_jurnal(f"PRODUKSI-{produksi.id}"):
            ServiceProduksiPanen.sinkron_produksi(produksi)

    def _sinkron_mutasi(self, nomor_dokumen, tanggal, barang, tipe, jumlah, keterangan):
        mutasi, created = MutasiPersediaan.objects.get_or_create(
            nomor_dokumen=nomor_dokumen,
            defaults={
                "tanggal": tanggal,
                "barang": barang,
                "tipe_mutasi": tipe,
                "jumlah": jumlah,
                "harga_per_unit": barang.harga_beli,
                "saldo_setelah": barang.stok,
                "keterangan": keterangan,
            },
        )
        if created or not self._sudah_jurnal(f"MUTASI-{mutasi.id}"):
            ServicePersediaan.sinkron_mutasi(mutasi)

    def _sinkron_pembelian(self, nomor, defaults, barang, jumlah, harga_satuan):
        pembelian, created = PembelianBarang.objects.get_or_create(
            nomor_invoice=nomor,
            defaults={**defaults, "total": Decimal("0")},
        )
        if created or not self._sudah_jurnal(f"BELI-{pembelian.nomor_invoice}"):
            for field, value in defaults.items():
                setattr(pembelian, field, value)
            pembelian.save()
            ServicePembelian.sinkron_pembelian(
                pembelian, barang=barang, jumlah=jumlah, harga_satuan=harga_satuan
            )

    def _sinkron_penjualan(self, nomor, defaults, barang, jumlah, harga_satuan):
        penjualan, created = PenjualanBarang.objects.get_or_create(
            nomor_invoice=nomor,
            defaults={**defaults, "total": Decimal("0")},
        )
        if created or not self._sudah_jurnal(f"JUAL-{penjualan.nomor_invoice}"):
            for field, value in defaults.items():
                setattr(penjualan, field, value)
            penjualan.save()
            ServicePenjualan.sinkron_penjualan(
                penjualan, barang=barang, jumlah=jumlah, harga_satuan=harga_satuan
            )

    def _sinkron_penerimaan(self, nomor_bukti, defaults):
        penerimaan, created = PenerimaanPiutang.objects.get_or_create(
            nomor_bukti=nomor_bukti,
            defaults=defaults,
        )
        if created or not self._sudah_jurnal(f"PIUTANG-{penerimaan.nomor_bukti}"):
            ServicePenjualan.sinkron_penerimaan_piutang(penerimaan)

    def _sinkron_pembayaran_utang(self, nomor_bukti, defaults):
        pembayaran, created = PembayaranUtang.objects.get_or_create(
            nomor_bukti=nomor_bukti,
            defaults=defaults,
        )
        if created or not self._sudah_jurnal(f"UTANG-{pembayaran.nomor_bukti}"):
            ServicePembelian.sinkron_pembayaran_utang(pembayaran)

    def _cetak_ringkasan(self):
        self.stdout.write("  Customer: 3 | Supplier: 2 | Barang: 6")
        self.stdout.write("  Produksi & Panen: 4 | Mutasi Persediaan: 2")
        self.stdout.write("  Pembelian: 3 (2 Piutang + 1 Tunai) | Pembayaran Piutang: 2")
        self.stdout.write("  Penjualan: 4 (2 Piutang + 2 Tunai) | Penerimaan Piutang: 2")
        self.stdout.write("  Semua transaksi tersinkron jurnal & stok otomatis.")
        self.stdout.write("  Catatan: jalankan ulang aman — data yang sudah ada tidak ditimpa.")
