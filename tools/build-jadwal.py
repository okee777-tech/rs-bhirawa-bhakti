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
import html
import json
import re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "jadwal-dokter.csv"
HTML = ROOT / "dokter.html"
INDEX = ROOT / "index.html"
LAYANAN_CSV = ROOT / "data" / "layanan.csv"
GALERI_CSV = ROOT / "data" / "galeri.csv"
BERITA_CSV = ROOT / "data" / "berita.csv"
GALERI_HTML = ROOT / "galeri.html"
BERITA_HTML = ROOT / "berita.html"

MARK_MULAI = "<!-- JADWAL:MULAI -->"
MARK_SELESAI = "<!-- JADWAL:SELESAI -->"
IDX_MULAI = "<!-- DOKTER:MULAI -->"
IDX_SELESAI = "<!-- DOKTER:SELESAI -->"
LAY_MULAI = "<!-- LAYANAN:MULAI -->"
LAY_SELESAI = "<!-- LAYANAN:SELESAI -->"
GAL_MULAI = "<!-- GALERI:MULAI -->"
GAL_SELESAI = "<!-- GALERI:SELESAI -->"
BER_MULAI = "<!-- BERITA:MULAI -->"
BER_SELESAI = "<!-- BERITA:SELESAI -->"
BER_HOME_MULAI = "<!-- BERITA_HOME:MULAI -->"
BER_HOME_SELESAI = "<!-- BERITA_HOME:SELESAI -->"

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


def foto_url(raw, size="w400"):
    """Kolom 'Foto' -> URL gambar siap pakai (drive thumbnail / URL langsung).

    Mendukung:
      - link Google Drive:  /file/d/<ID>/view, /open?id=<ID>, /uc?id=<ID>
      - ID Drive mentah (kode panjang saja)
      - URL gambar langsung (*.jpg/png/webp/gif)
    Mengembalikan "" bila tidak dikenali (agar tampil avatar inisial).
    """
    s = str(raw or "").strip()
    if not s:
        return ""
    if re.search(r"\.(png|jpe?g|webp|gif)(\?|$)", s, re.I):
        return s
    m = (re.search(r"/d/([A-Za-z0-9_-]{10,})", s)
         or re.search(r"[?&]id=([A-Za-z0-9_-]{10,})", s))
    fid = m.group(1) if m else ""
    if not fid and re.fullmatch(r"[A-Za-z0-9_-]{20,}", s):
        fid = s
    if not fid:
        return ""
    return f"https://drive.google.com/thumbnail?id={fid}&sz={size}"


def initials(name):
    """Inisial untuk avatar bila belum ada foto (buang dr./drg. dan gelar)."""
    kept = []
    for tok in re.split(r"[\s,]+", clean_nama(name)):
        tok = tok.strip()
        if not tok:
            continue
        low = tok.lower()
        if low in ("dr", "dr.", "drg", "drg."):
            continue
        if "." in tok:  # gelar: Sp.A / M.Biomed / dsb.
            continue
        kept.append(tok)
    letters = [t[0].upper() for t in kept[:2]]
    return "".join(letters) or "DR"


def scroll_wrap(inner, cls):
    """Bungkus carousel dengan tombol geser kiri/kanan."""
    return (f'<div class="scroll-wrap">\n'
            f'  <button type="button" class="scroll-btn scroll-btn-left" aria-label="Geser kiri">‹</button>\n'
            f'  <div class="{cls}">\n{inner}\n  </div>\n'
            f'  <button type="button" class="scroll-btn scroll-btn-right" aria-label="Geser kanan">›</button>\n'
            f'</div>')


def build_blocks(rows):
    """CSV -> daftar blok HTML per poli (kartu dokter, sudah urut)."""
    # filter & kelompokkan
    by_poli = OrderedDict()
    for r in rows:
        if r["sumber"] != "praktek":
            continue
        poli = r["poli"]
        by_poli.setdefault(poli, OrderedDict())
        dok = by_poli[poli].setdefault(
            r["dokter"], {"spes": r["spesialisasi"],
                          "foto": r.get("foto", ""),
                          "slots": OrderedDict()})
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
        cards = []
        for name, d in doctors.items():
            nama = html.escape(clean_nama(name))
            url = foto_url(d.get("foto", ""))
            if url:
                avatar = (f'<div class="doctor-avatar">'
                          f'<img src="{html.escape(url)}" alt="{nama}" loading="lazy"></div>')
            else:
                avatar = f'<div class="doctor-avatar">{html.escape(initials(name))}</div>'
            spes = (f'<div class="spec">{html.escape(d["spes"])}</div>'
                    if d["spes"] else "")
            lines = []
            for slot, days in d["slots"].items():
                lines.append(f'<div class="sched-line">'
                             f'<b>{html.escape(format_hari(days))}</b> {html.escape(jam_str(*slot))}</div>')
            schedule = '<div class="schedule">' + "".join(lines) + "</div>"
            cards.append(
                f'<div class="card doctor-card">\n'
                f'  {avatar}\n'
                f'  <h3>{nama}</h3>\n'
                f'  {spes}\n'
                f'  {schedule}\n'
                f'</div>'
            )
        grid = '<div class="doctor-grid">\n' + "\n".join(cards) + "\n</div>"
        blocks.append(f'<h2 class="poli-title">{icon} {html.escape(poli)}</h2>\n{grid}')
    return blocks


def poli_spec(poli):
    """Label spesialisasi singkat untuk kartu beranda (dari nama poli)."""
    base = re.sub(r"^Poli\s+", "", poli)
    base = re.sub(r"\s*\(.*?\)", "", base)
    if base.lower().startswith("gigi"):
        return base
    return "Spesialis " + base


def compact_schedule(slots):
    """Ringkasan jadwal singkat untuk kartu beranda."""
    all_days = set()
    times = set()
    for (m, s), days in slots.items():
        all_days.update(days)
        times.add(jam_str(m, s))
    hari = format_hari(all_days)
    if len(times) == 1:
        return (f'Jadwal: <b>{html.escape(hari)}</b><br />'
                f'{html.escape(times.pop())} WIB')
    return f'Jadwal: <b>{html.escape(hari)}</b><br />Lihat jadwal lengkap'


def build_home_cards(rows):
    """Semua dokter -> kartu untuk beranda (scroll horizontal)."""
    by_poli = OrderedDict()
    for r in rows:
        if r["sumber"] != "praktek":
            continue
        poli = r["poli"]
        by_poli.setdefault(poli, OrderedDict())
        dok = by_poli[poli].setdefault(
            r["dokter"], {"foto": r.get("foto", ""), "slots": OrderedDict()})
        key = (r["jam_mulai"], r["jam_selesai"])
        dok["slots"].setdefault(key, []).append(HARI_IDX[r["hari"]])

    order_map = {name: i for i, (name, _) in enumerate(POLI_ORDER)}
    polis = sorted(by_poli.keys(), key=lambda p: order_map.get(p, len(POLI_ORDER)))

    cards = []
    for poli in polis:
        for name, d in by_poli[poli].items():
            nama = html.escape(clean_nama(name))
            url = foto_url(d.get("foto", ""))
            avatar = (f'<div class="doctor-avatar">'
                      f'<img src="{html.escape(url)}" alt="{nama}" loading="lazy"></div>'
                      if url else f'<div class="doctor-avatar">{html.escape(initials(name))}</div>')
            spec = html.escape(poli_spec(poli))
            schedule = compact_schedule(d["slots"])
            cards.append(
                f'<div class="card doctor-card">\n'
                f'  {avatar}\n'
                f'  <h3>{nama}</h3>\n'
                f'  <div class="spec">{spec}</div>\n'
                f'  <div class="schedule">{schedule}</div>\n'
                f'</div>'
            )
    return scroll_wrap("\n".join(cards), "doctor-scroll")


def build_layanan():
    """Kartu layanan + data modal untuk beranda (dari data/layanan.csv)."""
    if not LAYANAN_CSV.exists():
        return None
    with LAYANAN_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows = [r for r in rows if (r.get("layanan") or "").strip()]
    if not rows:
        return None

    cards, data = [], []
    for i, r in enumerate(rows):
        nama = (r.get("layanan") or "").strip()
        ikon = (r.get("ikon") or "").strip() or "🏥"
        deskripsi = (r.get("deskripsi") or "").strip()
        telepon = (r.get("telepon") or "").strip()
        jadwal = (r.get("jadwal") or "").strip()
        foto = foto_url(r.get("foto", ""), size="w800")

        cards.append(
            f'<div class="card service-card" data-layanan="{i}" role="button" tabindex="0">\n'
            f'  <div class="icon">{html.escape(ikon)}</div>\n'
            f'  <h3>{html.escape(nama)}</h3>\n'
            f'  <p>{html.escape(deskripsi)}</p>\n'
            f'  <span class="service-more">Lihat info &amp; jadwal →</span>\n'
            f'</div>'
        )
        data.append({
            "nama": nama,
            "ikon": ikon,
            "deskripsi": deskripsi,
            "foto": foto,
            "telepon": telepon,
            "jadwal": jadwal,
        })

    scroll = scroll_wrap("\n".join(cards), "service-scroll")
    script = ('<script>window.LAYANAN_DATA = '
              + json.dumps(data, ensure_ascii=False)
              + ';</script>')
    return scroll + "\n" + script


def build_galeri():
    """Grid foto galeri + data lightbox (dari data/galeri.csv)."""
    if not GALERI_CSV.exists():
        return None
    with GALERI_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows = [r for r in rows if (r.get("judul") or "").strip()]
    if not rows:
        return None

    items, data = [], []
    for i, r in enumerate(rows):
        judul = (r.get("judul") or "").strip()
        kategori = (r.get("kategori") or "").strip()
        deskripsi = (r.get("deskripsi") or "").strip()
        tanggal = (r.get("tanggal") or "").strip()
        foto = foto_url(r.get("foto", ""), size="w800")

        if foto:
            thumb = (f'<div class="gallery-thumb">'
                     f'<img src="{html.escape(foto)}" alt="{html.escape(judul)}" loading="lazy"></div>')
        else:
            thumb = '<div class="gallery-thumb">🖼️</div>'
        cat = (f'<span class="gallery-cat">{html.escape(kategori)}</span>'
               if kategori else "")
        items.append(
            f'<div class="card gallery-item" data-galeri="{i}" role="button" tabindex="0">\n'
            f'  {thumb}\n'
            f'  <div class="gallery-cap">\n'
            f'    <h3>{html.escape(judul)}</h3>\n'
            f'    {cat}\n'
            f'  </div>\n'
            f'</div>'
        )
        data.append({
            "judul": judul, "kategori": kategori, "deskripsi": deskripsi,
            "tanggal": tanggal, "foto": foto,
        })

    grid = '<div class="gallery-grid">\n' + "\n".join(items) + '\n</div>'
    script = ('<script>window.GALERI_DATA = '
              + json.dumps(data, ensure_ascii=False)
              + ';</script>')
    return grid + "\n" + script


def berita_data():
    """Baca data/berita.csv -> (list kartu HTML, list data modal), atau None."""
    if not BERITA_CSV.exists():
        return None
    with BERITA_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows = [r for r in rows if (r.get("judul") or "").strip()]
    if not rows:
        return None

    items, data = [], []
    for i, r in enumerate(rows):
        judul = (r.get("judul") or "").strip()
        tanggal = (r.get("tanggal") or "").strip()
        kategori = (r.get("kategori") or "").strip()
        ringkasan = (r.get("ringkasan") or "").strip()
        isi = (r.get("isi") or "").strip()
        foto = foto_url(r.get("foto", ""), size="w800")

        if foto:
            thumb = (f'<div class="news-thumb">'
                     f'<img src="{html.escape(foto)}" alt="{html.escape(judul)}" loading="lazy"></div>')
        else:
            thumb = '<div class="news-thumb">📰</div>'
        meta_parts = [p for p in (kategori, tanggal) if p]
        meta = (f'<span class="meta">{html.escape(" · ".join(meta_parts))}</span>'
                if meta_parts else "")
        ringkas = f'<p>{html.escape(ringkasan)}</p>' if ringkasan else ""
        items.append(
            f'<div class="card news-card" data-berita="{i}" role="button" tabindex="0">\n'
            f'  {thumb}\n'
            f'  <div class="news-body">\n'
            f'    {meta}\n'
            f'    <h3>{html.escape(judul)}</h3>\n'
            f'    {ringkas}\n'
            f'    <span class="more">Baca selengkapnya →</span>\n'
            f'  </div>\n'
            f'</div>'
        )
        data.append({
            "judul": judul, "tanggal": tanggal, "kategori": kategori,
            "ringkasan": ringkasan, "isi": isi, "foto": foto,
        })
    return items, data


def build_berita():
    """Daftar berita + data modal untuk halaman berita.html."""
    res = berita_data()
    if not res:
        return None
    items, data = res
    lst = '<div class="news-list">\n' + "\n".join(items) + '\n</div>'
    script = ('<script>window.BERITA_DATA = '
              + json.dumps(data, ensure_ascii=False)
              + ';</script>')
    return lst + "\n" + script


def build_berita_home(limit=6):
    """Carousel berita + data modal untuk beranda (index.html)."""
    res = berita_data()
    if not res:
        return None
    items, data = res
    items = items[:limit]
    data = data[:limit]
    scroll = scroll_wrap("\n".join(items), "news-scroll")
    script = ('<script>window.BERITA_DATA = '
              + json.dumps(data, ensure_ascii=False)
              + ';</script>')
    return scroll + "\n" + script


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

    # --- Beranda: kartu dokter (preview) ---
    if INDEX.exists():
        idx = INDEX.read_text(encoding="utf-8")
        if IDX_MULAI in idx and IDX_SELESAI in idx:
            home = build_home_cards(rows)
            k1 = idx.index(IDX_MULAI) + len(IDX_MULAI)
            k2 = idx.index(IDX_SELESAI)
            idx = idx[:k1] + "\n" + home + "\n      " + idx[k2:]
            INDEX.write_text(idx, encoding="utf-8")
            print(f"✅ index.html ditulis ulang: {n_dok} kartu dokter beranda.")
        else:
            print(f"⚠️ penanda {IDX_MULAI}/{IDX_SELESAI} tidak ada di index.html (beranda dilewati).")
    else:
        print("⚠️ index.html tidak ditemukan.")

    # --- Beranda: kartu layanan (klik -> modal) ---
    if INDEX.exists():
        idx = INDEX.read_text(encoding="utf-8")
        if LAY_MULAI in idx and LAY_SELESAI in idx:
            lay = build_layanan()
            if lay:
                l1 = idx.index(LAY_MULAI) + len(LAY_MULAI)
                l2 = idx.index(LAY_SELESAI)
                idx = idx[:l1] + "\n" + lay + "\n      " + idx[l2:]
                INDEX.write_text(idx, encoding="utf-8")
                n_lay = lay.count('class="card service-card"')
                print(f"✅ index.html: {n_lay} kartu layanan ditulis.")
            else:
                print("⚠️ data/layanan.csv kosong/tidak ada — kartu layanan dibiarkan apa adanya.")
        else:
            print(f"⚠️ penanda {LAY_MULAI}/{LAY_SELESAI} tidak ada di index.html.")

    # --- Beranda: carousel berita terbaru ---
    if INDEX.exists():
        idx = INDEX.read_text(encoding="utf-8")
        if BER_HOME_MULAI in idx and BER_HOME_SELESAI in idx:
            bhome = build_berita_home()
            if bhome:
                h1 = idx.index(BER_HOME_MULAI) + len(BER_HOME_MULAI)
                h2 = idx.index(BER_HOME_SELESAI)
                idx = idx[:h1] + "\n" + bhome + "\n      " + idx[h2:]
                INDEX.write_text(idx, encoding="utf-8")
                n_bh = bhome.count('class="card news-card"')
                print(f"✅ index.html: {n_bh} berita beranda ditulis.")
            else:
                print("⚠️ data/berita.csv kosong/tidak ada — berita beranda dibiarkan apa adanya.")
        else:
            print(f"⚠️ penanda {BER_HOME_MULAI}/{BER_HOME_SELESAI} tidak ada di index.html.")

    # --- Galeri ---
    if GALERI_HTML.exists():
        ghtml = GALERI_HTML.read_text(encoding="utf-8")
        if GAL_MULAI in ghtml and GAL_SELESAI in ghtml:
            gal = build_galeri()
            if gal:
                g1 = ghtml.index(GAL_MULAI) + len(GAL_MULAI)
                g2 = ghtml.index(GAL_SELESAI)
                ghtml = ghtml[:g1] + "\n" + gal + "\n      " + ghtml[g2:]
                GALERI_HTML.write_text(ghtml, encoding="utf-8")
                n_gal = gal.count('class="card gallery-item"')
                print(f"✅ galeri.html: {n_gal} foto ditulis.")
            else:
                print("⚠️ data/galeri.csv kosong/tidak ada — galeri dibiarkan apa adanya.")
        else:
            print(f"⚠️ penanda {GAL_MULAI}/{GAL_SELESAI} tidak ada di galeri.html.")

    # --- Berita ---
    if BERITA_HTML.exists():
        bhtml = BERITA_HTML.read_text(encoding="utf-8")
        if BER_MULAI in bhtml and BER_SELESAI in bhtml:
            ber = build_berita()
            if ber:
                b1 = bhtml.index(BER_MULAI) + len(BER_MULAI)
                b2 = bhtml.index(BER_SELESAI)
                bhtml = bhtml[:b1] + "\n" + ber + "\n      " + bhtml[b2:]
                BERITA_HTML.write_text(bhtml, encoding="utf-8")
                n_ber = ber.count('class="card news-card"')
                print(f"✅ berita.html: {n_ber} berita ditulis.")
            else:
                print("⚠️ data/berita.csv kosong/tidak ada — berita dibiarkan apa adanya.")
        else:
            print(f"⚠️ penanda {BER_MULAI}/{BER_SELESAI} tidak ada di berita.html.")


if __name__ == "__main__":
    main()
