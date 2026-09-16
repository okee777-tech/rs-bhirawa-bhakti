#!/usr/bin/env python3
"""
Bangun ulang blok jadwal di dokter.html dari data/jadwal-dokter.csv.

Sumber : data/jadwal-dokter.csv (dihasilkan tools/extract-jadwal.py)
Aturan : HANYA baris `sumber == "praktek"` yang ditampilkan.
          (Anastesi & Radiologi ber-sumber "jam_kerja" -> otomatis dilewati,
           karena itu jam jaga, bukan jadwal praktek poli.)

Output : menulis ulang isi di antara penanda
         <!-- JADWAL:MULAI --> ... <!-- JADWAL:SELESAI --> pada dokter.html
"""
import csv
import re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "jadwal-dokter.csv"
HTML = ROOT / "dokter.html"

MARK_MULAI = "<!-- JADWAL:MULAI -->"
MARK_SELESAI = "<!-- JADWAL:SELESAI -->"

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
HARI_IDX = {h: i for i, h in enumerate(HARI)}

# Urutan tampil poli + ikon. Poli lain yang tidak terdaftar ikut di belakang.
POLI_ORDER = [
    ("Poli Anak", "👶"),
    ("Poli Bedah", "🔪"),
    ("Poli Kandungan (Obgyn)", "🤰"),
    ("Poli Penyakit Dalam", "🩺"),
    ("Poli Jantung", "❤️"),
    ("Poli Saraf", "🧠"),
    ("Poli THT-KL", "👂"),
    ("Poli Gigi Spesialis", "🦷"),
]
ICON_DEFAULT = "🏥"


# Bentuk baku gelar spesialis (agar "Sp. pd" / "Sp PD" / "Sp.perio" -> "Sp.PD" dst).
DEGREE = {
    "sp.a": "Sp.A", "sp.b": "Sp.B", "sp.og": "Sp.OG", "sp.pd": "Sp.PD",
    "sp.jp": "Sp.JP", "sp.s": "Sp.S", "sp.n": "Sp.N", "sp.tht-kl": "Sp.THT-KL",
    "sp.bm": "Sp.BM", "sp.kg": "Sp.KG", "sp.kga": "Sp.KGA", "sp.perio": "Sp.Perio",
    "sp.rad": "Sp.Rad", "m.biomed": "M.Biomed",
}


def clean_nama(s):
    """Rapikan nama: spasi/koma, awalan dr./drg., Title Case, gelar Sp. dibakukan."""
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    s = re.sub(r"\bdrg\b\s*\.?", "drg. ", s, flags=re.I)  # drg / drg. -> "drg. "
    s = re.sub(r"\bdr\b\s*\.?", "dr. ", s, flags=re.I)    # dr / dr. / DR -> "dr. "
    # bakukan gelar: "Sp. OG" -> "Sp.OG", "Sp S." -> "Sp.S", "M.biomed" -> "M.Biomed"
    s = re.sub(r"\bSp\.\s+([A-Za-z-]+)", lambda m: "Sp." + m.group(1).upper(), s)
    s = re.sub(r"\bSp\s+([A-Za-z])\.", r"Sp.\1", s)
    s = re.sub(r"\bM\.\s*([A-Za-z]+)", lambda m: "M." + m.group(1).capitalize(), s)
    s = re.sub(r"\s+", " ", s).strip()
    out = []
    for tok in s.split():
        low = tok.lower().strip(",.")
        if low in ("dr", "drg"):
            out.append(low + ".")
        elif low in DEGREE:
            out.append(DEGREE[low])
        elif "." in tok:
            out.append(".".join(p.capitalize() for p in tok.split(".")))
        else:
            out.append(tok.capitalize())
    r = " ".join(out)
    r = re.sub(r"([A-Za-z])\s+(Sp\.)", r"\1, \2", r)       # "...M Sp.PD" -> "...M, Sp.PD"
    r = re.sub(r"(Sp\.[A-Za-z-]+)\s+(M\.)", r"\1, \2", r)  # "Sp.S M.Biomed" -> "Sp.S, M.Biomed"
    r = re.sub(r"\s+([,.])", r"\1", r)
    r = re.sub(r",(?!\s)", ", ", r)
    return r.strip()


def format_hari(days_idx):
    """Kumpulan indeks hari -> string kompak: 'Senin – Jumat', 'Senin, Rabu'."""
    days_idx = sorted(set(days_idx))
    runs, run = [], [days_idx[0]]
    for d in days_idx[1:]:
        if d == run[-1] + 1:
            run.append(d)
        else:
            runs.append(run)
            run = [d]
    runs.append(run)
    parts = []
    for r in runs:
        if len(r) >= 3:
            parts.append(f"{HARI[r[0]]} – {HARI[r[-1]]}")
        else:
            parts.extend(HARI[i] for i in r)
    return ", ".join(parts)


def jam_str(mulai, selesai):
    return f"{mulai} – {selesai}"


def build_blocks(rows):
    """CSV -> daftar blok HTML per poli (sudah urut)."""
    # filter & kelompokkan
    by_poli = OrderedDict()
    for r in rows:
        if r["sumber"] != "praktek":
            continue
        poli = r["poli"]
        by_poli.setdefault(poli, OrderedDict())
        dok = by_poli[poli].setdefault(
            r["dokter"], {"spes": r["spesialisasi"], "slots": OrderedDict()})
        key = (r["jam_mulai"], r["jam_selesai"])
        dok["slots"].setdefault(key, []).append(HARI_IDX[r["hari"]])

    # urutkan poli
    order_map = {name: i for i, (name, _) in enumerate(POLI_ORDER)}
    polis = sorted(by_poli.keys(), key=lambda p: order_map.get(p, len(POLI_ORDER)))
    icons = dict(POLI_ORDER)

    blocks = []
    for poli in polis:
        icon = icons.get(poli, ICON_DEFAULT)
        doctors = by_poli[poli]
        has_spes = any(d["spes"] for d in doctors.values())
        head = "<tr><th>Dokter</th>"
        if has_spes:
            head += "<th>Spesialisasi</th>"
        head += "<th>Hari</th><th>Jam</th></tr>"

        trs = []
        for name, d in doctors.items():
            entries = [(format_hari(days), jam_str(*slot)) for slot, days in d["slots"].items()]
            n = len(entries)
            for i, (hari, jam) in enumerate(entries):
                cells = []
                if i == 0:
                    cells.append(f'<td rowspan="{n}"><strong>{clean_nama(name)}</strong></td>')
                    if has_spes:
                        cells.append(f'<td rowspan="{n}">{d["spes"]}</td>')
                cells.append(f"<td>{hari}</td>")
                cells.append(f"<td>{jam}</td>")
                trs.append("<tr>" + "".join(cells) + "</tr>")

        tbody = "".join(trs)
        blocks.append(
            f'<h2 class="poli-title">{icon} {poli}</h2>\n'
            f'<div class="table-wrap">\n'
            f'  <table class="schedule">\n'
            f'    <thead>{head}</thead>\n'
            f'    <tbody>{tbody}</tbody>\n'
            f'  </table>\n'
            f'</div>'
        )
    return blocks


def main():
    if not CSV.exists():
        raise SystemExit(f"FAIL: {CSV} belum ada. Jalankan tools/extract-jadwal.py dulu.")
    with CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    praktek = [r for r in rows if r["sumber"] == "praktek"]
    if not praktek:
        raise SystemExit("FAIL: tidak ada baris sumber=praktek di CSV.")

    html = HTML.read_text(encoding="utf-8")
    if MARK_MULAI not in html or MARK_SELESAI not in html:
        raise SystemExit(f"FAIL: penanda {MARK_MULAI}/{MARK_SELESAI} tidak ada di {HTML.name}")

    blocks = build_blocks(rows)
    generated = "\n\n".join(blocks)
    i1 = html.index(MARK_MULAI) + len(MARK_MULAI)
    i2 = html.index(MARK_SELESAI)
    html = html[:i1] + "\n" + generated + "\n      " + html[i2:]
    HTML.write_text(html, encoding="utf-8")

    n_poli = len(blocks)
    n_dok = len({r["dokter"] for r in praktek})
    print(f"✅ dokter.html ditulis ulang: {n_poli} poli, {n_dok} dokter, "
          f"{len(praktek)} slot jadwal.")


if __name__ == "__main__":
    main()
