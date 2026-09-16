#!/usr/bin/env python3
"""Bandingkan jadwal hasil ekstraksi xlsx vs yang tampil di dokter.html.

Normalisasi: nama dibandingkan tanpa spasi/titik; hari dipecah per hari
("Senin – Jumat" -> Senin..Jumat); kolom Spesialisasi pada tabel gigi diabaikan.
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "jadwal-dokter.csv"
HTML = ROOT / "dokter.html"

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def key_nama(s):
    s = strip_tags(s).lower()
    s = re.sub(r"\b(dr|drg|dokter)\b\.?", "", s)
    return re.sub(r"[^a-z]", "", s)


def norm_jam(s):
    m = re.search(r"(\d{1,2})[.:](\d{2})\s*[-–—]\s*(\d{1,2})[.:](\d{2})", strip_tags(s))
    return f"{int(m.group(1)):02d}.{m.group(2)}-{int(m.group(3)):02d}.{m.group(4)}" if m else ""


def expand_hari(s):
    """'Senin, Rabu, Jumat' -> [Senin, Rabu, Jumat]; 'Rabu – Jumat' -> Rabu..Jumat."""
    s = strip_tags(s)
    m = re.search(r"\b(Senin|Selasa|Rabu|Kamis|Jumat|Sabtu|Minggu)\s*[–-]\s*"
                  r"(Senin|Selasa|Rabu|Kamis|Jumat|Sabtu|Minggu)\b", s)
    if m:
        a, b = HARI.index(m.group(1)), HARI.index(m.group(2))
        return HARI[a:b + 1]
    return [h for h in HARI if re.search(rf"\b{h}", s, re.I)]


def parse_html():
    html = HTML.read_text(encoding="utf-8")
    out = {}
    for blok in re.split(r'<h2 class="poli-title">', html)[1:]:
        poli = re.sub(r"^(?:[^\w(]+)\s*", "", strip_tags(blok.split("</h2>")[0])).strip()
        tb = re.search(r'<table class="schedule">(.*?)</table>', blok, re.S)
        if not tb:
            continue
        isi = tb.group(1)
        ths = [strip_tags(x).lower() for x in re.findall(r"<th[^>]*>(.*?)</th>", isi, re.S)]
        header = re.search(r"<thead>(.*?)</thead>", isi, re.S)
        if header:
            ths = [strip_tags(x).lower() for x in re.findall(r"<th[^>]*>(.*?)</th>", header.group(1), re.S)]
        i_hari = next((i for i, t in enumerate(ths) if "hari" in t), len(ths) - 2)
        i_jam = next((i for i, t in enumerate(ths) if "jam" in t), len(ths) - 1)
        dokter = ""
        for tr in re.findall(r"<tr>(.*?)</tr>", isi, re.S):
            tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            if not tds:
                continue
            if "<strong>" in tds[0]:
                dokter = key_nama(tds[0])
            if not dokter:
                continue
            if len(tds) == len(ths):
                sel_hari, sel_jam = tds[i_hari], tds[i_jam]
            elif len(tds) >= 2:  # baris lanjutan rowspan: 2 kolom terakhir = hari, jam
                sel_hari, sel_jam = tds[-2], tds[-1]
            else:
                continue
            jam = norm_jam(sel_jam)
            if not jam:
                continue
            for h in expand_hari(sel_hari):
                out.setdefault((poli, dokter), set()).add((h, jam))
    return out


def parse_csv():
    out = {}
    with CSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.setdefault((r["poli"], key_nama(r["dokter"])), set()).add(
                (r["hari"], f"{r['jam_mulai']}-{r['jam_selesai']}"))
    return out


def main():
    web, xls = parse_html(), parse_csv()
    print(f"WEBSITE: {sum(map(len, web.values()))} slot | {len(web)} dokter-poli")
    print(f"XLSX   : {sum(map(len, xls.values()))} slot | {len(xls)} dokter-poli\n")

    print("### Ada di XLSX, TIDAK ada di website")
    for (p, d) in sorted(set(xls) - set(web)):
        print(f"  - {p}: {d}")
    print("\n### Ada di website, TIDAK ada di XLSX")
    for (p, d) in sorted(set(web) - set(xls)):
        print(f"  - {p}: {d}")

    print("\n### PERBEDAAN JADWAL (dokter yang ada di dua-duanya)")
    n_beda = 0
    for k in sorted(set(web) & set(xls)):
        hanya_web = web[k] - xls[k]
        hanya_xls = xls[k] - web[k]
        if not (hanya_web or hanya_xls):
            continue
        n_beda += 1
        print(f"\n  {k[0]} / {k[1]}")
        for h, j in sorted(hanya_web):
            print(f"    hanya di WEBSITE : {h} {j}")
        for h, j in sorted(hanya_xls):
            print(f"    hanya di XLSX    : {h} {j}")

    cocok = len(set(web) & set(xls)) - n_beda
    print(f"\nRingkas: {cocok} dokter-poli identik, {n_beda} berbeda, "
          f"{len(set(xls) - set(web))} hanya di xlsx, {len(set(web) - set(xls))} hanya di website.")


if __name__ == "__main__":
    main()
