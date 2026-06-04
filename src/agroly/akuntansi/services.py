from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Max, Min, Sum

from agroly.utils.format_rupiah import format_rupiah, format_rupiah_neraca

from .models import Akun, JurnalDetail, JurnalHeader

BULAN_ID = (
    "",
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
)

KATEGORI_LABA_RUGI = (
    ("pendapatan", "Pendapatan", "Penjualan"),
    ("hpp", "HPP", "Harga Pokok Penjualan"),
    ("beban_operasional", "Beban Operasional", "Beban Operasional"),
    ("pendapatan_lain", "Pendapatan Lain-lain", "Pendapatan Lain-lain"),
    ("beban_lain", "Beban Lain-lain", "Beban Lain-lain"),
)

SUBGRUP_ASET_TETAP = (
    ("121", "Tanah"),
    ("122", "Bangunan"),
    ("123", "Kendaraan"),
    ("124", "Peralatan"),
)

PREFIX_ARUS_OPERASI_ASET = ("112", "113", "114")
PREFIX_ARUS_OPERASI_UTANG = ("211", "212")
KODE_ARUS_PENYUSUTAN = ("61106", "61107", "61108")
PREFIX_ARUS_INVESTASI = ("121", "122", "123", "124")
PREFIX_ARUS_PENDANAAN = ("311", "312", "313")

KATEGORI_SALDO_NORMAL_KREDIT = (
    "kewajiban",
    "ekuitas",
    "pendapatan",
    "pendapatan_lain",
)


@dataclass
class BarisJurnal:
    akun: Akun
    debit: Decimal = Decimal("0")
    kredit: Decimal = Decimal("0")


class ServiceJurnal:
    @staticmethod
    def validasi_keseimbangan(daftar_baris: list[BarisJurnal]) -> None:
        if len(daftar_baris) < 2:
            raise ValueError("Jurnal harus memiliki minimal dua baris.")

        for idx, baris in enumerate(daftar_baris, start=1):
            debit = baris.debit or Decimal("0")
            kredit = baris.kredit or Decimal("0")
            if debit < 0 or kredit < 0:
                raise ValueError(f"Baris jurnal ke-{idx} memiliki nilai negatif.")
            if debit > 0 and kredit > 0:
                raise ValueError(
                    f"Baris jurnal ke-{idx} tidak valid. Isi debit atau kredit, bukan keduanya."
                )
            if debit == 0 and kredit == 0:
                raise ValueError(f"Baris jurnal ke-{idx} tidak memiliki nilai.")

        total_debit = sum((baris.debit for baris in daftar_baris), Decimal("0"))
        total_kredit = sum((baris.kredit for baris in daftar_baris), Decimal("0"))
        if total_debit != total_kredit:
            raise ValueError("Jurnal tidak balance. Total debit harus sama dengan total kredit.")

    @staticmethod
    def hapus_berdasarkan_nomor_bukti(nomor_bukti: str) -> None:
        if nomor_bukti:
            JurnalHeader.objects.filter(nomor_bukti=nomor_bukti).delete()

    @staticmethod
    @transaction.atomic
    def ganti_isi_jurnal(header: JurnalHeader, daftar_baris: list[BarisJurnal]) -> JurnalHeader:
        ServiceJurnal.validasi_keseimbangan(daftar_baris)
        header.detail_jurnal.all().delete()
        JurnalDetail.objects.bulk_create(
            [
                JurnalDetail(
                    jurnal_header=header,
                    akun=baris.akun,
                    debit=baris.debit,
                    kredit=baris.kredit,
                )
                for baris in daftar_baris
            ]
        )
        return header

    @staticmethod
    @transaction.atomic
    def posting_jurnal_otomatis(
        *,
        tanggal,
        nomor_bukti: str,
        keterangan: str,
        sumber_transaksi: str,
        daftar_baris: list[BarisJurnal],
    ) -> JurnalHeader:
        ServiceJurnal.validasi_keseimbangan(daftar_baris)
        ServiceJurnal.hapus_berdasarkan_nomor_bukti(nomor_bukti)
        header = JurnalHeader.objects.create(
            tanggal=tanggal,
            nomor_bukti=nomor_bukti,
            keterangan=keterangan,
            sumber_transaksi=sumber_transaksi,
        )
        JurnalDetail.objects.bulk_create(
            [
                JurnalDetail(
                    jurnal_header=header,
                    akun=baris.akun,
                    debit=baris.debit,
                    kredit=baris.kredit,
                )
                for baris in daftar_baris
            ]
        )
        return header

    @staticmethod
    def nomor_penyesuaian_baru(tanggal=None) -> str:
        from django.utils import timezone

        tanggal = tanggal or timezone.localdate()
        prefix = f"ADJ-{tanggal.strftime('%Y%m')}-"
        terakhir = (
            JurnalHeader.objects.filter(
                sumber_transaksi="penyesuaian",
                nomor_bukti__startswith=prefix,
            )
            .order_by("-nomor_bukti")
            .values_list("nomor_bukti", flat=True)
            .first()
        )
        urut = 1
        if terakhir:
            try:
                urut = int(terakhir.rsplit("-", 1)[-1]) + 1
            except ValueError:
                urut = 1
        return f"{prefix}{urut:03d}"


class ServiceLaporanKeuangan:
    @staticmethod
    def _format_rp(nilai: Decimal) -> str:
        return format_rupiah(nilai)

    @staticmethod
    def _format_rp_neraca(nilai: Decimal) -> str:
        return format_rupiah_neraca(nilai)

    @staticmethod
    def _label_per_tanggal_akhir() -> str:
        akhir = JurnalHeader.objects.aggregate(akhir=Max("tanggal"))["akhir"]
        if not akhir:
            return "Belum ada transaksi"
        return f"Per {akhir.day} {BULAN_ID[akhir.month]} {akhir.year}"

    @staticmethod
    def _rentang_periode():
        rentang = JurnalHeader.objects.aggregate(awal=Min("tanggal"), akhir=Max("tanggal"))
        return rentang["awal"], rentang["akhir"]

    @staticmethod
    def _label_periode_arus_kas() -> str:
        awal, akhir = ServiceLaporanKeuangan._rentang_periode()
        if not awal or not akhir:
            return "Belum ada transaksi"
        if awal == akhir:
            return f"{BULAN_ID[awal.month]} {awal.year}"
        if awal.year == akhir.year:
            return f"{BULAN_ID[awal.month]} {awal.year} s/d {BULAN_ID[akhir.month]} {akhir.year}"
        return f"{BULAN_ID[awal.month]} {awal.year} s/d {BULAN_ID[akhir.month]} {akhir.year}"

    @staticmethod
    def _mutasi_akun_periode(akun: Akun, awal, akhir) -> Decimal:
        agregat = JurnalDetail.objects.filter(
            akun=akun,
            jurnal_header__tanggal__gte=awal,
            jurnal_header__tanggal__lte=akhir,
        ).aggregate(total_debit=Sum("debit"), total_kredit=Sum("kredit"))
        debit = agregat["total_debit"] or Decimal("0")
        kredit = agregat["total_kredit"] or Decimal("0")
        return debit - kredit

    @staticmethod
    def _saldo_kas_per(tanggal) -> Decimal:
        if not tanggal:
            return Decimal("0")
        total = Decimal("0")
        for akun in Akun.objects.filter(kode_akun__startswith="111", aktif=True):
            agregat = JurnalDetail.objects.filter(
                akun=akun,
                jurnal_header__tanggal__lte=tanggal,
            ).aggregate(total_debit=Sum("debit"), total_kredit=Sum("kredit"))
            debit = agregat["total_debit"] or Decimal("0")
            kredit = agregat["total_kredit"] or Decimal("0")
            total += debit - kredit
        return total

    @staticmethod
    def _saldo_kas_sebelum(tanggal) -> Decimal:
        if not tanggal:
            return Decimal("0")
        return ServiceLaporanKeuangan._saldo_kas_per(tanggal - timedelta(days=1))

    @staticmethod
    def _baris_arus_kas(nama: str, nilai: Decimal) -> dict:
        return {
            "nama": nama,
            "nilai": nilai,
            "nilai_display": ServiceLaporanKeuangan._format_rp_neraca(nilai),
        }

    @staticmethod
    def _akun_arus_operasi(awal, akhir) -> list[dict]:
        baris = []
        for akun in Akun.objects.filter(aktif=True).order_by("kode_akun"):
            if akun.kode_akun.startswith("111"):
                continue
            if akun.kode_akun in KODE_ARUS_PENYUSUTAN:
                mutasi = ServiceLaporanKeuangan._mutasi_akun_periode(akun, awal, akhir)
                nilai = mutasi
                if nilai:
                    baris.append(ServiceLaporanKeuangan._baris_arus_kas(akun.nama_akun, nilai))
                continue
            if any(akun.kode_akun.startswith(p) for p in PREFIX_ARUS_OPERASI_ASET):
                mutasi = ServiceLaporanKeuangan._mutasi_akun_periode(akun, awal, akhir)
                nilai = -mutasi
                if nilai:
                    baris.append(ServiceLaporanKeuangan._baris_arus_kas(akun.nama_akun, nilai))
                continue
            if any(akun.kode_akun.startswith(p) for p in PREFIX_ARUS_OPERASI_UTANG):
                mutasi = ServiceLaporanKeuangan._mutasi_akun_periode(akun, awal, akhir)
                nilai = -mutasi
                if nilai:
                    baris.append(ServiceLaporanKeuangan._baris_arus_kas(akun.nama_akun, nilai))
        return baris

    @staticmethod
    def _akun_arus_investasi(awal, akhir) -> list[dict]:
        baris = []
        for akun in Akun.objects.filter(aktif=True).order_by("kode_akun"):
            if not any(akun.kode_akun.startswith(p) for p in PREFIX_ARUS_INVESTASI):
                continue
            mutasi = ServiceLaporanKeuangan._mutasi_akun_periode(akun, awal, akhir)
            nilai = -mutasi
            if nilai:
                baris.append(ServiceLaporanKeuangan._baris_arus_kas(akun.nama_akun, nilai))
        return baris

    @staticmethod
    def _akun_arus_pendanaan(awal, akhir) -> list[dict]:
        baris = []
        for akun in Akun.objects.filter(aktif=True).order_by("kode_akun"):
            if not any(akun.kode_akun.startswith(p) for p in PREFIX_ARUS_PENDANAAN):
                continue
            if akun.kode_akun == "31401":
                continue
            mutasi = ServiceLaporanKeuangan._mutasi_akun_periode(akun, awal, akhir)
            nilai = -mutasi
            if nilai:
                baris.append(ServiceLaporanKeuangan._baris_arus_kas(akun.nama_akun, nilai))
        return baris

    @staticmethod
    def saldo_akun(akun: Akun) -> Decimal:
        agregat = JurnalDetail.objects.filter(akun=akun).aggregate(
            total_debit=Sum("debit"),
            total_kredit=Sum("kredit"),
        )
        debit = agregat["total_debit"] or Decimal("0")
        kredit = agregat["total_kredit"] or Decimal("0")
        if akun.kategori_akun in KATEGORI_SALDO_NORMAL_KREDIT:
            return kredit - debit
        return debit - kredit

    @staticmethod
    def balance_akun_untuk_daftar(akun: Akun) -> dict:
        saldo = ServiceLaporanKeuangan.saldo_akun(akun)
        return {"saldo": saldo}

    @staticmethod
    def _saldo_akun_neraca(akun: Akun) -> Decimal:
        return ServiceLaporanKeuangan.saldo_akun(akun)

    @staticmethod
    def _baris_akun_neraca(akun: Akun) -> dict | None:
        saldo = ServiceLaporanKeuangan._saldo_akun_neraca(akun)
        if saldo == 0:
            return None
        return {
            "nama": akun.nama_akun,
            "kode_akun": akun.kode_akun,
            "nilai": saldo,
            "nilai_display": ServiceLaporanKeuangan._format_rp_neraca(saldo),
        }

    @staticmethod
    def _grup_akun_dari_queryset(akun_qs, nama_grup: str, label_total: str) -> dict | None:
        baris = []
        for akun in akun_qs:
            item = ServiceLaporanKeuangan._baris_akun_neraca(akun)
            if item:
                baris.append(item)
        if not baris:
            return None
        total = sum((b["nilai"] for b in baris), Decimal("0"))
        return {
            "nama": nama_grup,
            "baris": baris,
            "total": total,
            "total_label": label_total,
            "total_display": ServiceLaporanKeuangan._format_rp_neraca(total),
        }

    @staticmethod
    def _total_dari_grup(daftar_grup: list) -> Decimal:
        return sum((grup["total"] for grup in daftar_grup if grup), Decimal("0"))

    @staticmethod
    def _label_periode_laba_rugi() -> str:
        rentang = JurnalHeader.objects.aggregate(
            awal=Min("tanggal"),
            akhir=Max("tanggal"),
        )
        awal, akhir = rentang["awal"], rentang["akhir"]
        if not awal or not akhir:
            return "Belum ada transaksi"
        if awal == akhir:
            return f"{awal.day} {BULAN_ID[awal.month]} {awal.year}"
        if awal.year == akhir.year and awal.month == akhir.month:
            return f"{awal.day}–{akhir.day} {BULAN_ID[awal.month]} {awal.year}"
        if awal.year == akhir.year:
            return f"{BULAN_ID[awal.month]} s/d {BULAN_ID[akhir.month]} {awal.year}"
        return f"{BULAN_ID[awal.month]} {awal.year} s/d {BULAN_ID[akhir.month]} {akhir.year}"

    @staticmethod
    def _saldo_akun_laba_rugi(akun: Akun) -> Decimal:
        return ServiceLaporanKeuangan.saldo_akun(akun)

    @staticmethod
    def hitung_laba_rugi_terstruktur():
        sections = []
        total_pendapatan = Decimal("0")
        total_beban = Decimal("0")

        for kategori, judul_bagian, judul_grup in KATEGORI_LABA_RUGI:
            baris_akun = []
            for akun in Akun.objects.filter(kategori_akun=kategori, aktif=True).order_by("kode_akun"):
                saldo = ServiceLaporanKeuangan._saldo_akun_laba_rugi(akun)
                if saldo == 0:
                    continue
                baris_akun.append(
                    {
                        "nama": akun.nama_akun,
                        "kode_akun": akun.kode_akun,
                        "nilai": saldo,
                        "nilai_display": ServiceLaporanKeuangan._format_rp(saldo),
                    }
                )

            if not baris_akun:
                continue

            total_grup = sum((baris["nilai"] for baris in baris_akun), Decimal("0"))
            label_total_grup = (
                "Total Penjualan"
                if kategori == "pendapatan"
                else f"Total {judul_grup}"
            )

            sections.append(
                {
                    "nama": judul_bagian,
                    "total_label": f"Total {judul_bagian}",
                    "total": total_grup,
                    "total_display": ServiceLaporanKeuangan._format_rp(total_grup),
                    "grup": [
                        {
                            "nama": judul_grup,
                            "baris": baris_akun,
                            "total": total_grup,
                            "total_label": label_total_grup,
                            "total_display": ServiceLaporanKeuangan._format_rp(total_grup),
                        }
                    ],
                }
            )

            if kategori in ("pendapatan", "pendapatan_lain"):
                total_pendapatan += total_grup
            else:
                total_beban += total_grup

        laba_bersih = total_pendapatan - total_beban
        return {
            "judul": "Laporan Laba Rugi",
            "periode": ServiceLaporanKeuangan._label_periode_laba_rugi(),
            "sections": sections,
            "total_pendapatan": total_pendapatan,
            "total_beban": total_beban,
            "laba_bersih": laba_bersih,
            "laba_bersih_display": ServiceLaporanKeuangan._format_rp(laba_bersih),
        }

    @staticmethod
    def hitung_laba_rugi():
        detail = ServiceLaporanKeuangan.hitung_laba_rugi_terstruktur()
        return {
            "pendapatan": detail["total_pendapatan"],
            "beban": detail["total_beban"],
            "laba_bersih": detail["laba_bersih"],
        }

    @staticmethod
    def hitung_neraca_terstruktur():
        aset_lancar = ServiceLaporanKeuangan._grup_akun_dari_queryset(
            Akun.objects.filter(kode_akun__startswith="11", aktif=True).order_by("kode_akun"),
            "Aset Lancar",
            "Total Aset Lancar",
        )

        subgrup_tetap = []
        for prefix, nama_sub in SUBGRUP_ASET_TETAP:
            grup = ServiceLaporanKeuangan._grup_akun_dari_queryset(
                Akun.objects.filter(kode_akun__startswith=prefix, aktif=True).order_by(
                    "kode_akun"
                ),
                nama_sub,
                f"Total {nama_sub}",
            )
            if grup:
                subgrup_tetap.append(grup)

        total_aset_tetap = ServiceLaporanKeuangan._total_dari_grup(subgrup_tetap)
        aset_tetap = None
        if subgrup_tetap:
            aset_tetap = {
                "nama": "Aset Tetap",
                "subgrup": subgrup_tetap,
                "total": total_aset_tetap,
                "total_label": "Total Aset Tetap",
                "total_display": ServiceLaporanKeuangan._format_rp_neraca(total_aset_tetap),
            }

        total_aset = Decimal("0")
        if aset_lancar:
            total_aset += aset_lancar["total"]
        if aset_tetap:
            total_aset += aset_tetap["total"]

        bagian_aset = {
            "nama": "Aset",
            "aset_lancar": aset_lancar,
            "aset_tetap": aset_tetap,
            "total_label": "Total Aset",
            "total": total_aset,
            "total_display": ServiceLaporanKeuangan._format_rp_neraca(total_aset),
        }

        baris_kewajiban = []
        for akun in Akun.objects.filter(kode_akun__startswith="21", aktif=True).order_by(
            "kode_akun"
        ):
            item = ServiceLaporanKeuangan._baris_akun_neraca(akun)
            if item:
                baris_kewajiban.append(item)
        total_kewajiban = sum((b["nilai"] for b in baris_kewajiban), Decimal("0"))

        net_assets = total_aset - total_kewajiban

        baris_modal = []
        label_khusus = {"31101": "Modal Awal", "31301": "Laba Ditahan"}
        for akun in Akun.objects.filter(kode_akun__startswith="31", aktif=True).order_by(
            "kode_akun"
        ):
            if akun.kode_akun == "31401":
                continue
            item = ServiceLaporanKeuangan._baris_akun_neraca(akun)
            if item:
                if akun.kode_akun in label_khusus:
                    item = {**item, "nama": label_khusus[akun.kode_akun]}
                baris_modal.append(item)

        laba_bersih = ServiceLaporanKeuangan.hitung_laba_rugi()["laba_bersih"]
        sudah_ada_laba_ditahan = any(b.get("kode_akun") == "31301" for b in baris_modal)
        if laba_bersih != 0 and not sudah_ada_laba_ditahan:
            baris_modal.append(
                {
                    "nama": "Laba Tahun Berjalan",
                    "kode_akun": "",
                    "nilai": laba_bersih,
                    "nilai_display": ServiceLaporanKeuangan._format_rp_neraca(laba_bersih),
                }
            )

        total_modal = sum((b["nilai"] for b in baris_modal), Decimal("0"))
        bagian_kewajiban = {
            "tipe": "kewajiban",
            "nama": "Kewajiban",
            "baris": baris_kewajiban,
            "total_label": "Total Kewajiban",
            "total": total_kewajiban,
            "total_display": ServiceLaporanKeuangan._format_rp_neraca(total_kewajiban),
        }
        bagian_modal = {
            "tipe": "modal",
            "nama": "Modal",
            "baris": baris_modal,
            "total_label": "Total Modal",
            "total": total_modal,
            "total_display": ServiceLaporanKeuangan._format_rp_neraca(total_modal),
        }

        blocks = []
        if aset_lancar or aset_tetap:
            blocks.append({"tipe": "aset", **bagian_aset})
        if baris_kewajiban:
            blocks.append(bagian_kewajiban)
        if (aset_lancar or aset_tetap) and baris_modal:
            blocks.append(
                {
                    "tipe": "net_assets",
                    "nama": "Net Assets",
                    "total_display": ServiceLaporanKeuangan._format_rp_neraca(net_assets),
                }
            )
        if baris_modal:
            blocks.append(bagian_modal)

        return {
            "judul": "Laporan Posisi Keuangan",
            "periode": ServiceLaporanKeuangan._label_per_tanggal_akhir(),
            "blocks": blocks,
            "net_assets": net_assets,
            "net_assets_display": ServiceLaporanKeuangan._format_rp_neraca(net_assets),
            "total_aset": total_aset,
            "total_kewajiban": total_kewajiban,
            "total_modal": total_modal,
        }

    @staticmethod
    def hitung_neraca():
        detail = ServiceLaporanKeuangan.hitung_neraca_terstruktur()
        return {
            "aset": detail["total_aset"],
            "kewajiban": detail["total_kewajiban"],
            "ekuitas": detail["total_modal"],
        }

    @staticmethod
    def hitung_arus_kas_terstruktur():
        awal, akhir = ServiceLaporanKeuangan._rentang_periode()
        if not awal or not akhir:
            return {
                "judul": "Laporan Arus Kas",
                "periode": "Belum ada transaksi",
                "sections": [],
                "ringkasan": [],
            }

        laba_bersih = ServiceLaporanKeuangan.hitung_laba_rugi_terstruktur()["laba_bersih"]
        penyesuaian = ServiceLaporanKeuangan._akun_arus_operasi(awal, akhir)
        total_operasi = laba_bersih + sum((b["nilai"] for b in penyesuaian), Decimal("0"))

        penyesuaian_investasi = ServiceLaporanKeuangan._akun_arus_investasi(awal, akhir)
        total_investasi = sum((b["nilai"] for b in penyesuaian_investasi), Decimal("0"))

        penyesuaian_pendanaan = ServiceLaporanKeuangan._akun_arus_pendanaan(awal, akhir)
        total_pendanaan = sum((b["nilai"] for b in penyesuaian_pendanaan), Decimal("0"))

        net_change = total_operasi + total_investasi + total_pendanaan
        kas_awal = ServiceLaporanKeuangan._saldo_kas_sebelum(awal)
        kas_akhir = ServiceLaporanKeuangan._saldo_kas_per(akhir)

        sections = [
            {
                "nama": "Arus Kas dari Aktivitas Operasi",
                "laba_bersih": ServiceLaporanKeuangan._baris_arus_kas("Laba Bersih", laba_bersih),
                "penyesuaian": penyesuaian,
                "total_label": "Arus Kas Bersih dari Aktivitas Operasi",
                "total": total_operasi,
                "total_display": ServiceLaporanKeuangan._format_rp_neraca(total_operasi),
            },
            {
                "nama": "Arus Kas dari Aktivitas Investasi",
                "laba_bersih": None,
                "penyesuaian": penyesuaian_investasi,
                "total_label": "Arus Kas Bersih dari Aktivitas Investasi",
                "total": total_investasi,
                "total_display": ServiceLaporanKeuangan._format_rp_neraca(total_investasi),
            },
            {
                "nama": "Arus Kas dari Aktivitas Pendanaan",
                "laba_bersih": None,
                "penyesuaian": penyesuaian_pendanaan,
                "total_label": "Arus Kas Bersih dari Aktivitas Pendanaan",
                "total": total_pendanaan,
                "total_display": ServiceLaporanKeuangan._format_rp_neraca(total_pendanaan),
            },
        ]

        ringkasan = [
            ServiceLaporanKeuangan._baris_arus_kas(
                "Kenaikan/(Penurunan) Bersih untuk periode",
                net_change,
            ),
            ServiceLaporanKeuangan._baris_arus_kas(
                "Kas pada Awal Periode",
                kas_awal,
            ),
            {
                **ServiceLaporanKeuangan._baris_arus_kas(
                    "Kas pada Akhir Periode",
                    kas_akhir,
                ),
                "is_final": True,
            },
        ]

        return {
            "judul": "Laporan Arus Kas",
            "periode": ServiceLaporanKeuangan._label_periode_arus_kas(),
            "sections": sections,
            "ringkasan": ringkasan,
            "kas_masuk": max(net_change, Decimal("0")),
            "kas_keluar": abs(min(net_change, Decimal("0"))),
        }

    @staticmethod
    def hitung_arus_kas():
        detail = ServiceLaporanKeuangan.hitung_arus_kas_terstruktur()
        return {
            "kas_masuk": detail["kas_masuk"],
            "kas_keluar": detail["kas_keluar"],
        }

    @staticmethod
    def hitung_perubahan_ekuitas():
        modal_awal = (
            JurnalDetail.objects.filter(akun__kode_akun="31101").aggregate(total=Sum("kredit"))[
                "total"
            ]
            or Decimal("0")
        )
        prive = (
            JurnalDetail.objects.filter(akun__kode_akun="31201").aggregate(total=Sum("debit"))[
                "total"
            ]
            or Decimal("0")
        )
        laba_bersih = ServiceLaporanKeuangan.hitung_laba_rugi()["laba_bersih"]
        return {
            "modal_awal": modal_awal,
            "prive": prive,
            "laba_bersih": laba_bersih,
            "ekuitas_akhir": modal_awal + laba_bersih - prive,
        }

    @staticmethod
    def hitung_buku_besar():
        data = defaultdict(list)
        saldo_akun = defaultdict(lambda: Decimal("0"))
        detail = JurnalDetail.objects.select_related("jurnal_header", "akun").order_by(
            "jurnal_header__tanggal", "jurnal_header__nomor_bukti", "id"
        )
        for item in detail:
            kode = item.akun.kode_akun
            saldo_akun[kode] += item.debit - item.kredit
            data[kode].append(
                {
                    "tanggal": item.jurnal_header.tanggal,
                    "nomor_bukti": item.jurnal_header.nomor_bukti,
                    "akun": item.akun.nama_akun,
                    "debit": item.debit,
                    "kredit": item.kredit,
                    "saldo_berjalan": saldo_akun[kode],
                }
            )
        return dict(data)

    @staticmethod
    def hitung_neraca_saldo():
        ringkasan = []
        total_debit = Decimal("0")
        total_kredit = Decimal("0")
        for akun in Akun.objects.filter(aktif=True).order_by("kode_akun"):
            debit = (
                JurnalDetail.objects.filter(akun=akun).aggregate(total=Sum("debit"))["total"]
                or Decimal("0")
            )
            kredit = (
                JurnalDetail.objects.filter(akun=akun).aggregate(total=Sum("kredit"))["total"]
                or Decimal("0")
            )
            total_debit += debit
            total_kredit += kredit
            ringkasan.append(
                {
                    "kode_akun": akun.kode_akun,
                    "nama_akun": akun.nama_akun,
                    "total_debit": debit,
                    "total_kredit": kredit,
                }
            )
        return {
            "baris": ringkasan,
            "total_debit": total_debit,
            "total_kredit": total_kredit,
            "balance": total_debit == total_kredit,
        }
