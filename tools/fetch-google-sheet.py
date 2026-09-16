#!/usr/bin/env python3
"""
Ambil jadwal dokter dari Google Sheets (atau CSV lokal), lalu bangun ulang dokter.html.

Cara pakai:
  1) Google Sheet -> File -> Share -> Publish to web -> format CSV -> salin link.
  2) Jalankan:
        python3 tools/fetch-google-sheet.py "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"
     (link disimpan ke data/gsheet-url.txt, jadi berikutnya cukup:)
        python3 tools/fetch-google-sheet.py

Format kolom yang diharapkan (judul boleh beda kapital):
    Poli | Dokter | Spesialisasi | Hari | Jam Mulai | Jam Selesai
  - "Hari" boleh ditulis rentang, mis. "Senin - Jumat".
  - "Jam Mulai"/"Jam Selesai" bisa pakai titik atau titik-dua (15.00 / 15:00).
  - Hanya baris yang terisi di sheet ini yang tampil di website.

Output : data/jadwal-dokter.csv (kanonik) + dokter.html (dibangun ulang).
"""
import csv
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_OUT = DATA / "jadwal-dokter.csv"
URL_FILE = DATA / "gsheet-url.txt"
BUILD = ROOT / "tools" / "build-jadwal.py"

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
HARI_NORM = {
    "senin": "Senin", "selasa": "Selasa", "rabu": "Rabu", "kamis": "Kamis",
    "jumat": "Jumat", "sabtu": "Sabtu", "minggu": "Minggu",
    "ahad": "Minggu", "akad": "Minggu", "akhad": "Minggu",
}

# kolom kanonik -> kandidat nama header (dinormalisasi tanpa non-huruf)
COLS = {
    "poli": ["poli", "poliklinik", "klinik"],
    "dokter": ["dokter", "nama", "namadokter", "namadokterdan"],
    "spesialisasi": ["spesialisasi", "spesialis", "subspesialisasi"],
    "hari": ["hari", "hari praktek", "haripraktek"],
    "jam_mulai": ["jammulai", "mulai"],
    "jam_selesai": ["jamselesai", "selesai"],
}


def norm_hdr(h):
    return re.sub(r"[^a-z]", "", str(h or "").lower())


def find_cols(headers):
    """Header baris -> dict kolom kanonik: indeks kolom (0-based)."""
    found = {}
    for i, h in enumerate(headers):
        key = norm_hdr(h)
        for canon, cands in COLS.items():
            if canon not in found and key in cands:
                found[canon] = i
    return found


def norm_hari(v):
    s = re.sub(r"\s+", " ", str(v or "")).strip().lower()
    return HARI_NORM.get(s, "")


def expand_hari(v):
    """Teks hari -> daftar hari (urut Senin..Minggu).

    Diterima: 'Senin' | 'Senin - Jumat' | 'Senin, Rabu, Jumat'
              | 'Senin/Rabu' | 'Senin dan Jumat' | 'Setiap hari' | 'Hari kerja'.
    Mengembalikan [] kalau tidak dikenali (pemanggil WAJIB menolak, bukan mengabaikan).
    """
    s = re.sub(r"\s+", " ", str(v or "")).strip().lower()
    if not s:
        return []
    if "setiap hari" in s or s in ("harian", "tiap hari"):
        return list(HARI)
    if "hari kerja" in s or s in ("weekday", "weekdays"):
        return HARI[:5]
    m = re.search(r"(" + "|".join(HARI_NORM) + r")\s*[-–—]\s*(" + "|".join(HARI_NORM) + r")", s)
    if m:
        a, b = HARI.index(HARI_NORM[m.group(1)]), HARI.index(HARI_NORM[m.group(2)])
        if a <= b:
            return [HARI[i] for i in range(a, b + 1)]
    hari = []
    for bagian in re.split(r"[,/&;]|\bdan\b|\bserta\b", s):
        d = norm_hari(bagian.strip())
        if d and d not in hari:
            hari.append(d)
    return sorted(hari, key=HARI.index)


def norm_jam(v):
    m = re.search(r"(\d{1,2})[:.](\d{2})", str(v or ""))
    if not m:
        return ""
    return f"{int(m.group(1)):02d}.{m.group(2)}"


def read_source(src):
    """Download (http) atau baca file lokal -> teks CSV."""
    if src.startswith("http://") or src.startswith("https://"):
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8-sig")
    return Path(src).read_text(encoding="utf-8-sig")


def main():
    if len(sys.argv) > 1:
        src = sys.argv[1].strip()
        if src.startswith("http"):
            DATA.mkdir(parents=True, exist_ok=True)
            URL_FILE.write_text(src + "\n", encoding="utf-8")
    else:
        if URL_FILE.exists():
            src = URL_FILE.read_text(encoding="utf-8").strip().splitlines()[0]
        else:
            sys.exit("FAIL: beri URL Google Sheet sebagai argumen, "
                     "atau buat data/gsheet-url.txt")

    text = read_source(src)
    rows = list(csv.DictReader(text.splitlines()))
    if not rows:
        sys.exit("FAIL: CSV kosong / header tidak terbaca.")

    cols = find_cols(rows[0].keys())
    need = ["poli", "dokter", "hari", "jam_mulai", "jam_selesai"]
    missing = [c for c in need if c not in cols]
    if missing:
        sys.exit(f"FAIL: kolom tidak ditemukan: {missing}. Header terbaca: {list(rows[0].keys())}")

    def g(row, canon):
        i = cols.get(canon)
        if i is None:
            return ""
        return list(row.values())[i]

    out, warn, ditolak = [], [], []
    for row in rows:
        poli = g(row, "poli").strip()
        dokter = g(row, "dokter").strip()
        spes = g(row, "spesialisasi").strip() if "spesialisasi" in cols else ""
        jam_m = norm_jam(g(row, "jam_mulai"))
        jam_s = norm_jam(g(row, "jam_selesai"))
        if not (poli and dokter):
            continue  # baris kosong
        if not (jam_m and jam_s):
            warn.append(f"  - jam tidak valid: '{dokter}' / {g(row, 'hari')} "
                        f"({g(row, 'jam_mulai')} - {g(row, 'jam_selesai')})")
            continue
        hari_list = expand_hari(g(row, "hari"))
        if not hari_list:
            ditolak.append(f"  - {dokter} | hari terbaca: {g(row, 'hari')!r}")
            continue
        for hari in hari_list:
            out.append({
                "poli": poli, "dokter": dokter, "spesialisasi": spes,
                "hari": hari, "jam_mulai": jam_m, "jam_selesai": jam_s,
                "sumber": "praktek",
            })

    if ditolak:
        sys.exit("FAIL: ada baris dengan kolom HARI yang tidak dikenali — "
                 "tidak ada perubahan yang ditulis:\n" + "\n".join(ditolak)
                 + "\n  Format hari yang benar: Senin | Senin - Jumat | Senin, Rabu, Jumat")

    DATA.mkdir(parents=True, exist_ok=True)
    fields = ["poli", "dokter", "spesialisasi", "hari", "jam_mulai", "jam_selesai", "sumber"]
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)

    print(f"✅ {len(out)} baris jadwal dari sheet -> {CSV_OUT.name}")
    if warn:
        print("⚠️  peringatan:")
        print("\n".join(warn))

    # bangun ulang dokter.html
    subprocess.run([sys.executable, str(BUILD)], check=True)


if __name__ == "__main__":
    main()
