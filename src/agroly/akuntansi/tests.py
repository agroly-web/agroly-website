from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from agroly.akuntansi.models import Akun, JurnalHeader, JurnalDetail
from agroly.utils.format_rupiah import format_rupiah, format_rupiah_neraca
from agroly.akuntansi.kode_akun import (
    AKUN_POSTING_OTOMATIS,
    KAS_BANK,
    KAS_KECIL,
    PERLENGKAPAN,
    PIUTANG_USAHA,
    PENDAPATAN_PENJUALAN,
    UTANG_USAHA,
)
from agroly.akuntansi.services import BarisJurnal, ServiceJurnal, ServiceLaporanKeuangan
from agroly.pembelian.models import PembayaranUtang, PembelianBarang
from agroly.pembelian.services import ServicePembelian
from agroly.penjualan.models import PenerimaanPiutang, PenjualanBarang
from agroly.penjualan.services import ServicePenjualan
from agroly.persediaan.models import BarangPersediaan, MutasiPersediaan
from agroly.persediaan.services import ServicePersediaan
from agroly.produksi_panen.models import ProduksiPanen
from agroly.produksi_panen.services import ServiceProduksiPanen
from agroly.relasi_bisnis.models import Customer, Supplier


class FormatRupiahTests(TestCase):
    def test_format_rupiah_formal(self):
        self.assertEqual(format_rupiah(5000000), "Rp. 5.000.000")
        self.assertEqual(format_rupiah(-1250000), "-Rp. 1.250.000")

    def test_format_rupiah_neraca_negatif(self):
        self.assertEqual(format_rupiah_neraca(-500000), "(Rp. 500.000)")


class SiklusBisnisTerintegrasiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        akun_diperlukan = [
            ("11101", "Kas Kecil", "aset"),
            ("11102", "Kas di Bank", "aset"),
            ("11201", "Piutang Usaha", "aset"),
            ("11301", "Persediaan Barang Dagang", "aset"),
            ("11302", "Perlengkapan Kantor", "aset"),
            ("21101", "Utang Usaha", "kewajiban"),
            ("31101", "Modal Pemilik", "ekuitas"),
            ("41101", "Pendapatan Penjualan", "pendapatan"),
            ("51101", "Harga Pokok Penjualan", "hpp"),
            ("51201", "Pembelian Barang Dagang", "hpp"),
        ]
        for kode, nama, kategori in akun_diperlukan:
            Akun.objects.create(kode_akun=kode, nama_akun=nama, kategori_akun=kategori, aktif=True)

    def test_siklus_berkesinambungan_dari_operasional_ke_laporan(self):
        tanggal = timezone.now().date()
        supplier = Supplier.objects.create(nama="Supplier Uji")
        customer = Customer.objects.create(nama="Customer Uji")
        barang = BarangPersediaan.objects.create(
            kode_barang="BRG-UJI-01",
            nama_barang="Kelengkeng Uji",
            stok=Decimal("50"),
            satuan="kg",
            harga_beli=Decimal("10000"),
            harga_jual=Decimal("15000"),
            aktif=True,
        )

        produksi = ProduksiPanen.objects.create(
            tanggal=tanggal,
            komoditas="Kelengkeng Uji",
            grade="A",
            jumlah_hasil_panen=Decimal("30"),
            satuan="kg",
        )
        ServiceProduksiPanen.sinkron_produksi(produksi)

        pembelian = PembelianBarang.objects.create(
            tanggal=tanggal,
            supplier=supplier,
            nomor_invoice="INV-BELI-UJI-01",
            total=Decimal("0"),
            status_pembayaran="utang",
        )
        ServicePembelian.sinkron_pembelian(
            pembelian, barang=barang, jumlah=Decimal("20"), harga_satuan=Decimal("10000")
        )

        penjualan = PenjualanBarang.objects.create(
            tanggal=tanggal,
            customer=customer,
            nomor_invoice="INV-JUAL-UJI-01",
            total=Decimal("0"),
            status_pembayaran="piutang",
        )
        ServicePenjualan.sinkron_penjualan(
            penjualan, barang=barang, jumlah=Decimal("10"), harga_satuan=Decimal("15000")
        )

        penerimaan = PenerimaanPiutang.objects.create(
            tanggal=tanggal,
            customer=customer,
            nomor_bukti="TRM-UJI-01",
            jumlah_terima=Decimal("50000"),
        )
        ServicePenjualan.sinkron_penerimaan_piutang(penerimaan)

        pembayaran = PembayaranUtang.objects.create(
            tanggal=tanggal,
            supplier=supplier,
            nomor_bukti="BYR-UJI-01",
            jumlah_bayar=Decimal("50000"),
        )
        ServicePembelian.sinkron_pembayaran_utang(pembayaran)

        mutasi_manual = MutasiPersediaan.objects.create(
            tanggal=tanggal,
            barang=barang,
            tipe_mutasi="keluar",
            jumlah=Decimal("5"),
            saldo_setelah=barang.stok,
            keterangan="Penyesuaian uji",
        )
        ServicePersediaan.sinkron_mutasi(mutasi_manual)

        barang.refresh_from_db()
        self.assertEqual(barang.stok, Decimal("85"))
        mutasi_produksi = MutasiPersediaan.objects.get(keterangan=f"Produksi panen {produksi.id}")
        self.assertEqual(mutasi_produksi.barang_id, barang.id)
        self.assertFalse(JurnalHeader.objects.filter(nomor_bukti=f"PRODUKSI-{produksi.id}").exists())
        self.assertFalse(JurnalHeader.objects.filter(nomor_bukti=f"MUTASI-{mutasi_manual.id}").exists())
        self.assertTrue(JurnalHeader.objects.filter(nomor_bukti="BELI-INV-BELI-UJI-01").exists())
        self.assertTrue(JurnalHeader.objects.filter(nomor_bukti="JUAL-INV-JUAL-UJI-01").exists())
        self.assertTrue(JurnalHeader.objects.filter(nomor_bukti="PIUTANG-TRM-UJI-01").exists())
        self.assertTrue(JurnalHeader.objects.filter(nomor_bukti="UTANG-BYR-UJI-01").exists())

        laporan = ServiceLaporanKeuangan.hitung_neraca_saldo()
        self.assertTrue(laporan["balance"])
        self.assertGreaterEqual(laporan["total_debit"], Decimal("1"))
        self.assertGreaterEqual(laporan["total_kredit"], Decimal("1"))

    def test_penjualan_menolak_stok_minus(self):
        tanggal = timezone.now().date()
        customer = Customer.objects.create(nama="Customer Minus")
        barang = BarangPersediaan.objects.create(
            kode_barang="BRG-UJI-02",
            nama_barang="Barang Minus",
            stok=Decimal("1"),
            satuan="kg",
            harga_beli=Decimal("10000"),
            harga_jual=Decimal("15000"),
            aktif=True,
        )
        penjualan = PenjualanBarang.objects.create(
            tanggal=tanggal,
            customer=customer,
            nomor_invoice="INV-MINUS-01",
            total=Decimal("0"),
            status_pembayaran="tunai",
        )

        with self.assertRaisesMessage(ValueError, "Stok barang Barang Minus tidak mencukupi untuk penjualan."):
            ServicePenjualan.sinkron_penjualan(
                penjualan, barang=barang, jumlah=Decimal("2"), harga_satuan=Decimal("15000")
            )


class ServiceJurnalValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.akun_kas = Akun.objects.create(
            kode_akun="11101", nama_akun="Kas Kecil", kategori_akun="aset", aktif=True
        )
        cls.akun_pendapatan = Akun.objects.create(
            kode_akun="41101", nama_akun="Pendapatan Penjualan", kategori_akun="pendapatan", aktif=True
        )

    def test_validasi_jurnal_minimal_dua_baris(self):
        with self.assertRaisesMessage(ValueError, "Jurnal harus memiliki minimal dua baris."):
            ServiceJurnal.validasi_keseimbangan(
                [BarisJurnal(akun=self.akun_kas, debit=Decimal("1000"), kredit=Decimal("0"))]
            )

    def test_validasi_jurnal_satu_baris_harus_satu_sisi(self):
        with self.assertRaisesMessage(
            ValueError, "Baris jurnal ke-1 tidak valid. Isi debit atau kredit, bukan keduanya."
        ):
            ServiceJurnal.validasi_keseimbangan(
                [
                    BarisJurnal(akun=self.akun_kas, debit=Decimal("1000"), kredit=Decimal("1000")),
                    BarisJurnal(akun=self.akun_pendapatan, debit=Decimal("0"), kredit=Decimal("1000")),
                ]
            )

    def test_validasi_jurnal_mengharuskan_balance(self):
        with self.assertRaisesMessage(
            ValueError, "Jurnal tidak balance. Total debit harus sama dengan total kredit."
        ):
            ServiceJurnal.validasi_keseimbangan(
                [
                    BarisJurnal(akun=self.akun_kas, debit=Decimal("1000"), kredit=Decimal("0")),
                    BarisJurnal(akun=self.akun_pendapatan, debit=Decimal("0"), kredit=Decimal("900")),
                ]
            )


class JurnalInputFormTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="uji_jurnal_input", password="uji12345")
        self.client.force_login(self.user)
        self.akun_kas = Akun.objects.create(
            kode_akun="11110", nama_akun="Kas Uji Input", kategori_akun="aset", aktif=True
        )
        self.akun_modal = Akun.objects.create(
            kode_akun="31110", nama_akun="Modal Uji Input", kategori_akun="ekuitas", aktif=True
        )

    def test_input_jurnal_halaman_render(self):
        response = self.client.get("/akuntansi/jurnal/tambah/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail Jurnal")
        self.assertContains(response, "Pilih akun")

    def test_input_jurnal_simpan_dengan_baris_kosong_extra(self):
        tanggal = timezone.now().date().isoformat()
        response = self.client.post(
            "/akuntansi/jurnal/tambah/",
            {
                "tanggal": tanggal,
                "nomor_bukti": "MANUAL-001",
                "keterangan": "Uji input jurnal",
                "sumber_transaksi": "manual",
                "detail_jurnal-TOTAL_FORMS": "3",
                "detail_jurnal-INITIAL_FORMS": "0",
                "detail_jurnal-MIN_NUM_FORMS": "0",
                "detail_jurnal-MAX_NUM_FORMS": "1000",
                "detail_jurnal-0-akun": self.akun_kas.pk,
                "detail_jurnal-0-posisi": "debit",
                "detail_jurnal-0-nominal": "1000",
                "detail_jurnal-1-akun": self.akun_modal.pk,
                "detail_jurnal-1-posisi": "kredit",
                "detail_jurnal-1-nominal": "1000",
                "detail_jurnal-2-akun": "",
                "detail_jurnal-2-posisi": "",
                "detail_jurnal-2-nominal": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(JurnalHeader.objects.filter(nomor_bukti="MANUAL-001").exists())


class SaldoOperasionalTests(TestCase):
    """Balance daftar akun hanya dari aturan penjualan/pembelian (+ pelunasan)."""

    @classmethod
    def setUpTestData(cls):
        for kode, nama, kategori in [
            (KAS_KECIL, "Kas Kecil", "aset"),
            (KAS_BANK, "Kas di Bank", "aset"),
            (PIUTANG_USAHA, "Piutang Usaha", "aset"),
            (PERLENGKAPAN, "Perlengkapan Kantor", "aset"),
            (UTANG_USAHA, "Utang Usaha", "kewajiban"),
            (PENDAPATAN_PENJUALAN, "Pendapatan Penjualan", "pendapatan"),
        ]:
            Akun.objects.create(kode_akun=kode, nama_akun=nama, kategori_akun=kategori, aktif=True)
        cls.customer = Customer.objects.create(nama="Cust Saldo")
        cls.supplier = Supplier.objects.create(nama="Sup Saldo")
        cls.barang = BarangPersediaan.objects.create(
            kode_barang="BRG-SALDO",
            nama_barang="Barang Saldo",
            stok=Decimal("100"),
            satuan="kg",
            harga_beli=Decimal("10000"),
            harga_jual=Decimal("15000"),
            aktif=True,
        )

    def _saldo(self, kode: str) -> Decimal:
        return ServiceLaporanKeuangan.saldo_akun(Akun.objects.get(kode_akun=kode))

    def test_siklus_tunai_dan_piutang_saldo_akurat(self):
        tanggal = timezone.now().date()

        pembelian_tunai = PembelianBarang.objects.create(
            tanggal=tanggal,
            supplier=self.supplier,
            nomor_invoice="BELI-TUNAI-SALDO",
            total=Decimal("0"),
            status_pembayaran="tunai",
        )
        ServicePembelian.sinkron_pembelian(
            pembelian_tunai, self.barang, Decimal("10"), Decimal("10000")
        )
        pembelian_tunai.refresh_from_db()
        total_beli = pembelian_tunai.total

        penjualan_tunai = PenjualanBarang.objects.create(
            tanggal=tanggal,
            customer=self.customer,
            nomor_invoice="JUAL-TUNAI-SALDO",
            total=Decimal("0"),
            status_pembayaran="tunai",
        )
        ServicePenjualan.sinkron_penjualan(
            penjualan_tunai, self.barang, Decimal("4"), Decimal("15000")
        )
        penjualan_tunai.refresh_from_db()
        total_jual_tunai = penjualan_tunai.total

        penjualan_piutang = PenjualanBarang.objects.create(
            tanggal=tanggal,
            customer=self.customer,
            nomor_invoice="JUAL-PIUTANG-SALDO",
            total=Decimal("0"),
            status_pembayaran="piutang",
        )
        ServicePenjualan.sinkron_penjualan(
            penjualan_piutang, self.barang, Decimal("6"), Decimal("20000")
        )
        penjualan_piutang.refresh_from_db()
        total_jual_piutang = penjualan_piutang.total

        penerimaan = PenerimaanPiutang.objects.create(
            tanggal=tanggal,
            customer=self.customer,
            nomor_bukti="TRM-SALDO-01",
            jumlah_terima=Decimal("50000"),
        )
        ServicePenjualan.sinkron_penerimaan_piutang(penerimaan)

        self.assertEqual(self._saldo(KAS_KECIL), Decimal("0"))
        self.assertEqual(self._saldo(KAS_BANK), total_jual_tunai - total_beli + Decimal("50000"))
        self.assertEqual(self._saldo(PERLENGKAPAN), total_beli)
        self.assertEqual(self._saldo(PIUTANG_USAHA), total_jual_piutang - Decimal("50000"))
        self.assertEqual(self._saldo(PENDAPATAN_PENJUALAN), total_jual_tunai + total_jual_piutang)

        produksi = ProduksiPanen.objects.create(
            tanggal=tanggal,
            komoditas="Tes",
            grade="A",
            jumlah_hasil_panen=Decimal("50"),
            satuan="kg",
        )
        ServiceProduksiPanen.sinkron_produksi(produksi)
        self.assertEqual(self._saldo(KAS_BANK), total_jual_tunai - total_beli + Decimal("50000"))

        ServiceProduksiPanen.hapus_dampak_produksi(produksi)
        ServicePenjualan.hapus_dampak(penjualan_piutang)
        ServicePenjualan.hapus_dampak(penjualan_tunai)
        ServicePembelian.hapus_dampak(pembelian_tunai)
        ServicePenjualan.hapus_dampak_penerimaan_piutang(penerimaan)

        self.assertEqual(self._saldo(KAS_BANK), Decimal("0"))
        self.assertEqual(self._saldo(PERLENGKAPAN), Decimal("0"))
        self.assertEqual(self._saldo(PIUTANG_USAHA), Decimal("0"))
        self.assertEqual(self._saldo(PENDAPATAN_PENJUALAN), Decimal("0"))

    def test_posting_otomatis_tidak_menggunakan_kas_kecil(self):
        tanggal = timezone.now().date()
        penjualan = PenjualanBarang.objects.create(
            tanggal=tanggal,
            customer=self.customer,
            nomor_invoice="JUAL-NO-11101",
            total=Decimal("0"),
            status_pembayaran="tunai",
        )
        ServicePenjualan.sinkron_penjualan(
            penjualan, self.barang, Decimal("1"), Decimal("100000")
        )
        kode_terpakai = set(
            JurnalDetail.objects.filter(
                jurnal_header__sumber_transaksi__in=(
                    "penjualan",
                    "pembelian",
                    "penerimaan_piutang",
                    "pembayaran_utang",
                )
            ).values_list("akun__kode_akun", flat=True)
        )
        self.assertNotIn(KAS_KECIL, kode_terpakai)
        self.assertTrue(kode_terpakai.issubset(AKUN_POSTING_OTOMATIS))


class PostingJurnalOtomatisTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for kode, nama, kategori in [
            ("11102", "Kas di Bank", "aset"),
            ("11201", "Piutang Usaha", "aset"),
            ("11302", "Perlengkapan Kantor", "aset"),
            ("21101", "Utang Usaha", "kewajiban"),
            ("41101", "Pendapatan Penjualan", "pendapatan"),
            (KAS_KECIL, "Kas Kecil", "aset"),
        ]:
            Akun.objects.create(kode_akun=kode, nama_akun=nama, kategori_akun=kategori, aktif=True)
        cls.customer = Customer.objects.create(nama="Cust Jurnal")
        cls.supplier = Supplier.objects.create(nama="Sup Jurnal")
        cls.barang = BarangPersediaan.objects.create(
            kode_barang="BRG-JRN",
            nama_barang="Barang Jurnal",
            stok=Decimal("100"),
            satuan="kg",
            harga_beli=Decimal("1000"),
            harga_jual=Decimal("2000"),
            aktif=True,
        )

    def test_penjualan_tunai_debit_kas_bank(self):
        penjualan = PenjualanBarang.objects.create(
            tanggal=timezone.now().date(),
            customer=self.customer,
            nomor_invoice="JUAL-TUNAI-01",
            total=Decimal("0"),
            status_pembayaran="tunai",
        )
        ServicePenjualan.sinkron_penjualan(
            penjualan, self.barang, Decimal("2"), Decimal("5000")
        )
        penjualan.refresh_from_db()
        jurnal = JurnalHeader.objects.get(nomor_bukti="JUAL-JUAL-TUNAI-01")
        kas = jurnal.detail_jurnal.get(akun__kode_akun=KAS_BANK)
        self.assertEqual(kas.debit, penjualan.total)
        self.assertEqual(kas.kredit, Decimal("0"))

    def test_penjualan_piutang_debit_piutang_usaha(self):
        penjualan = PenjualanBarang.objects.create(
            tanggal=timezone.now().date(),
            customer=self.customer,
            nomor_invoice="JUAL-PIUTANG-01",
            total=Decimal("0"),
            status_pembayaran="piutang",
        )
        ServicePenjualan.sinkron_penjualan(
            penjualan, self.barang, Decimal("1"), Decimal("10000")
        )
        piutang = JurnalHeader.objects.get(
            nomor_bukti="JUAL-JUAL-PIUTANG-01"
        ).detail_jurnal.get(akun__kode_akun=PIUTANG_USAHA)
        self.assertGreater(piutang.debit, Decimal("0"))

    def test_pembelian_tunai_kredit_kas_debit_perlengkapan(self):
        pembelian = PembelianBarang.objects.create(
            tanggal=timezone.now().date(),
            supplier=self.supplier,
            nomor_invoice="BELI-TUNAI-01",
            total=Decimal("0"),
            status_pembayaran="tunai",
        )
        ServicePembelian.sinkron_pembelian(
            pembelian, self.barang, Decimal("3"), Decimal("4000")
        )
        pembelian.refresh_from_db()
        jurnal = JurnalHeader.objects.get(nomor_bukti="BELI-BELI-TUNAI-01")
        perlengkapan = jurnal.detail_jurnal.get(akun__kode_akun=PERLENGKAPAN)
        kas = jurnal.detail_jurnal.get(akun__kode_akun=KAS_BANK)
        self.assertEqual(perlengkapan.debit, pembelian.total)
        self.assertEqual(kas.kredit, pembelian.total)

    def test_edit_nomor_invoice_menghapus_jurnal_lama(self):
        pembelian = PembelianBarang.objects.create(
            tanggal=timezone.now().date(),
            supplier=self.supplier,
            nomor_invoice="BELI-LAMA",
            total=Decimal("0"),
            status_pembayaran="tunai",
        )
        ServicePembelian.sinkron_pembelian(
            pembelian, self.barang, Decimal("1"), Decimal("1000")
        )
        self.assertTrue(JurnalHeader.objects.filter(nomor_bukti="BELI-BELI-LAMA").exists())
        pembelian.nomor_invoice = "BELI-BARU"
        pembelian.save()
        ServicePembelian.sinkron_pembelian(
            pembelian,
            self.barang,
            Decimal("1"),
            Decimal("1000"),
            nomor_invoice_lama="BELI-LAMA",
        )
        self.assertFalse(JurnalHeader.objects.filter(nomor_bukti="BELI-BELI-LAMA").exists())
        self.assertTrue(JurnalHeader.objects.filter(nomor_bukti="BELI-BELI-BARU").exists())


class JurnalPenyesuaianTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="uji_penyesuaian", password="uji12345")
        self.client.force_login(self.user)
        self.akun_beban = Akun.objects.create(
            kode_akun="61120", nama_akun="Beban Penyesuaian Uji", kategori_akun="beban_operasional", aktif=True
        )
        self.akun_kas = Akun.objects.create(
            kode_akun="11120", nama_akun="Kas Penyesuaian Uji", kategori_akun="aset", aktif=True
        )

    def test_halaman_penyesuaian_list(self):
        response = self.client.get("/akuntansi/jurnal-penyesuaian/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jurnal Penyesuaian")

    def test_halaman_tambah_penyesuaian(self):
        response = self.client.get("/akuntansi/jurnal-penyesuaian/tambah/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No. Dokumen")
        self.assertContains(response, "Pilih akun")

    def test_nomor_penyesuaian_otomatis(self):
        tanggal = timezone.now().date()
        nomor = ServiceJurnal.nomor_penyesuaian_baru(tanggal)
        self.assertTrue(nomor.startswith(f"ADJ-{tanggal.strftime('%Y%m')}-"))

        response = self.client.post(
            "/akuntansi/jurnal-penyesuaian/tambah/",
            {
                "tanggal": tanggal.isoformat(),
                "nomor_bukti": "",
                "keterangan": "",
                "detail_jurnal-TOTAL_FORMS": "2",
                "detail_jurnal-INITIAL_FORMS": "0",
                "detail_jurnal-MIN_NUM_FORMS": "0",
                "detail_jurnal-MAX_NUM_FORMS": "1000",
                "detail_jurnal-0-akun": self.akun_beban.pk,
                "detail_jurnal-0-debit": "100",
                "detail_jurnal-0-kredit": "0",
                "detail_jurnal-1-akun": self.akun_kas.pk,
                "detail_jurnal-1-debit": "0",
                "detail_jurnal-1-kredit": "100",
            },
        )
        self.assertEqual(response.status_code, 302)
        header = JurnalHeader.objects.filter(sumber_transaksi="penyesuaian").latest("id")
        self.assertEqual(header.nomor_bukti, nomor)

    def test_simpan_penyesuaian_mempengaruhi_laporan(self):
        tanggal = timezone.now().date().isoformat()
        response = self.client.post(
            "/akuntansi/jurnal-penyesuaian/tambah/",
            {
                "tanggal": tanggal,
                "nomor_bukti": "ADJ-UJI-001",
                "keterangan": "Penyusutan uji",
                "detail_jurnal-TOTAL_FORMS": "2",
                "detail_jurnal-INITIAL_FORMS": "0",
                "detail_jurnal-MIN_NUM_FORMS": "0",
                "detail_jurnal-MAX_NUM_FORMS": "1000",
                "detail_jurnal-0-akun": self.akun_beban.pk,
                "detail_jurnal-0-debit": "500000",
                "detail_jurnal-0-kredit": "0",
                "detail_jurnal-1-akun": self.akun_kas.pk,
                "detail_jurnal-1-debit": "0",
                "detail_jurnal-1-kredit": "500000",
            },
        )
        self.assertEqual(response.status_code, 302)
        header = JurnalHeader.objects.get(nomor_bukti="ADJ-UJI-001")
        self.assertEqual(header.sumber_transaksi, "penyesuaian")

        saldo_beban = ServiceLaporanKeuangan.saldo_akun(self.akun_beban)
        self.assertEqual(saldo_beban, Decimal("500000"))

        response_list = self.client.get("/akuntansi/jurnal/")
        self.assertNotContains(response_list, "ADJ-UJI-001")

        response_penyesuaian = self.client.get("/akuntansi/jurnal-penyesuaian/")
        self.assertContains(response_penyesuaian, "ADJ-UJI-001")

    def test_edit_penyesuaian_memperbarui_saldo_akun(self):
        akun_beban = self.akun_beban
        akun_kas = self.akun_kas
        saldo_awal = ServiceLaporanKeuangan.saldo_akun(akun_beban)

        self.client.post(
            "/akuntansi/jurnal-penyesuaian/tambah/",
            {
                "tanggal": timezone.now().date().isoformat(),
                "nomor_bukti": "ADJ-EDIT-01",
                "keterangan": "Awal",
                "detail_jurnal-TOTAL_FORMS": "2",
                "detail_jurnal-INITIAL_FORMS": "0",
                "detail_jurnal-MIN_NUM_FORMS": "0",
                "detail_jurnal-MAX_NUM_FORMS": "1000",
                "detail_jurnal-0-akun": akun_beban.pk,
                "detail_jurnal-0-debit": "1000",
                "detail_jurnal-0-kredit": "0",
                "detail_jurnal-1-akun": akun_kas.pk,
                "detail_jurnal-1-debit": "0",
                "detail_jurnal-1-kredit": "1000",
            },
        )
        header = JurnalHeader.objects.get(nomor_bukti="ADJ-EDIT-01")
        self.assertEqual(ServiceLaporanKeuangan.saldo_akun(akun_beban), saldo_awal + Decimal("1000"))

        self.client.post(
            f"/akuntansi/jurnal-penyesuaian/{header.pk}/edit/",
            {
                "tanggal": timezone.now().date().isoformat(),
                "nomor_bukti": "ADJ-EDIT-01",
                "keterangan": "Diubah",
                "detail_jurnal-TOTAL_FORMS": "2",
                "detail_jurnal-INITIAL_FORMS": "2",
                "detail_jurnal-MIN_NUM_FORMS": "0",
                "detail_jurnal-MAX_NUM_FORMS": "1000",
                "detail_jurnal-0-id": header.detail_jurnal.all()[0].pk,
                "detail_jurnal-0-akun": akun_beban.pk,
                "detail_jurnal-0-debit": "2500",
                "detail_jurnal-0-kredit": "0",
                "detail_jurnal-1-id": header.detail_jurnal.all()[1].pk,
                "detail_jurnal-1-akun": akun_kas.pk,
                "detail_jurnal-1-debit": "0",
                "detail_jurnal-1-kredit": "2500",
            },
        )
        self.assertEqual(ServiceLaporanKeuangan.saldo_akun(akun_beban), saldo_awal + Decimal("2500"))
        self.assertEqual(header.detail_jurnal.count(), 2)

        self.client.post(f"/akuntansi/jurnal-penyesuaian/{header.pk}/hapus/")
        self.assertEqual(ServiceLaporanKeuangan.saldo_akun(akun_beban), saldo_awal)


class JurnalViewRegressionTests(TestCase):
    def test_halaman_jurnal_list_tidak_error(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="uji_jurnal", password="uji12345")
        self.client.force_login(user)

        akun = Akun.objects.create(
            kode_akun="11109", nama_akun="Kas Uji View", kategori_akun="aset", aktif=True
        )
        header = JurnalHeader.objects.create(
            tanggal=timezone.now().date(),
            nomor_bukti="VIEW-001",
            keterangan="Uji render jurnal list",
            sumber_transaksi="manual",
        )
        JurnalDetail.objects.create(jurnal_header=header, akun=akun, debit=Decimal("100"), kredit=Decimal("0"))
        JurnalDetail.objects.create(jurnal_header=header, akun=akun, debit=Decimal("0"), kredit=Decimal("100"))

        response = self.client.get("/akuntansi/jurnal/")
        self.assertEqual(response.status_code, 200)
