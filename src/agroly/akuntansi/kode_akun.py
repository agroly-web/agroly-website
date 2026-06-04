"""Kode akun standar AGROLY untuk posting jurnal otomatis operasional.

Hanya modul berikut yang boleh menambah jurnal otomatis ke daftar akun:
- penjualan (tunai/piutang)
- penerimaan_piutang
- pembelian (tunai/utang)
- pembayaran_utang
- jurnal penyesuaian (manual akuntansi)
- jurnal manual

Produksi panen dan mutasi persediaan TIDAK memposting jurnal.
"""

KAS_KECIL = "11101"
KAS_BANK = "11102"
PIUTANG_USAHA = "11201"
PERSEDIAAN_DAGANG = "11301"
PERLENGKAPAN = "11302"
UTANG_USAHA = "21101"
PENDAPATAN_PENJUALAN = "41101"
HPP = "51101"

# Akun yang dipakai posting otomatis operasional (selain jurnal manual/penyesuaian)
AKUN_POSTING_OTOMATIS = frozenset(
    {
        KAS_BANK,
        PIUTANG_USAHA,
        PERLENGKAPAN,
        UTANG_USAHA,
        PENDAPATAN_PENJUALAN,
    }
)
