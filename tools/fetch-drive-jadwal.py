#!/usr/bin/env python3
"""
Ambil jadwal dokter dari Google Drive (akun gog yang sudah terotorisasi),
lalu bangun ulang dokter.html.

Cara pakai:
    python3 tools/fetch-drive-jadwal.py <fileId> [--sheet "NamaTab"]
    python3 tools/fetch-drive-jadwal.py            # pakai ID tersimpan

Sumber bisa berupa:
  - file CSV biasa di Drive, atau
  - Google Sheet native (diekspor otomatis jadi CSV oleh Drive API).
    Mode "auto" (bawaan) memakai jalur ini. Mode "sheet" memakai Sheets API —
    hanya berguna kalau API itu sudah diaktifkan di project Google Cloud.

ID sumber disimpan di data/drive-source.json supaya berikutnya cukup jalankan
tanpa argumen.

Aturan kolom & normalisasi hari/jam disamakan dengan tools/fetch-google-sheet.py
(header: Poli | Dokter | Spesialisasi | Hari | Jam Mulai | Jam Selesai).
Output: data/jadwal-dokter.csv (kanonik) + dokter.html dibangun ulang.
"""
import csv
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_OUT = DATA / "jadwal-dokter.csv"
DRIVE_CFG = DATA / "drive-source.json"
HELPERS = ROOT / "tools" / "fetch-google-sheet.py"
BUILD = ROOT / "tools" / "build-jadwal.py"
GOG = os.environ.get("GOG_BIN", "gog")
ACCOUNT = os.environ.get("GOG_ACCOUNT", "auto")


def load_helpers():
    """Pakai ulang fungsi normalisasi dari fetch-google-sheet.py (tanpa duplikasi)."""
    spec = importlib.util.spec_from_file_location("fetch_gs", HELPERS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def gog(*args, **kw):
    cmd = [GOG, "--account", ACCOUNT, *args]
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        pesan = (r.stderr or r.stdout or "").strip()
        if any(t in pesan for t in ("invalid_grant", "Token has been expired",
                                    "revoked", "401", "Unauthorized")):
            raise SystemExit(
                "FAIL: akses Google Drive sudah tidak berlaku (token mati).\n"
                "  Perbaiki dengan otorisasi ulang:\n"
                "    gog auth add casemixrsbbmalang@gmail.com "
                "--services drive,sheets --force-consent\n"
                f"  (pesan asli: {pesan.splitlines()[0][:120]})")
        raise SystemExit(f"FAIL: {' '.join(cmd)}\n{pesan}")
    return r.stdout


def read_csv_file(file_id):
    with tempfile.TemporaryDirectory() as tmp:
        gog("drive", "download", file_id, "--out", tmp)
        files = list(Path(tmp).glob("*"))
        if not files:
            raise SystemExit("FAIL: tidak ada berkas terunduh dari Drive.")
        return files[0].read_text(encoding="utf-8-sig")


def read_sheet_via_api(file_id, tab="Sheet1"):
    # Range terbuka "A:F" (semua baris) — bukan "A1:F500", agar jadwal tidak
    # terpotong diam-diam kalau barisnya melebihi 500.
    out = gog("sheets", "get", file_id, f"{tab}!A:F", "--json")
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        raise SystemExit(f"FAIL: keluaran sheets tidak berupa JSON:\n{out[:400]}")
    values = payload.get("values") or payload.get("rows") or []
    if values and isinstance(values[0], dict):  # bentuk {values:[{...}]}
        values = [list(v.values()) for v in values]
    return values


def values_to_rows(values, h):
    """Daftar baris (list) -> list dict dengan header kanonik."""
    if not values:
        raise SystemExit("FAIL: sheet kosong.")
    headers = [str(x).strip() for x in values[0]]
    idx = {}
    for i, hd in enumerate(headers):
        key = h.norm_hdr(hd)
        for canon, cands in h.COLS.items():
            if canon not in idx and key in cands:
                idx[canon] = i
    missing = [c for c in ("poli", "dokter", "hari", "jam_mulai", "jam_selesai") if c not in idx]
    if missing:
        raise SystemExit(f"FAIL: kolom tidak ditemukan: {missing}. Header: {headers}")
    rows = []
    for r in values[1:]:
        r = list(r) + [""] * (len(headers) - len(r))
        rows.append({c: str(r[i]).strip() for c, i in idx.items()})
    return rows


def csv_text_to_rows(text, h):
    rows = list(csv.DictReader(text.splitlines()))
    if not rows:
        raise SystemExit("FAIL: CSV kosong / header tidak terbaca.")
    idx = h.find_cols(rows[0].keys())
    missing = [c for c in ("poli", "dokter", "hari", "jam_mulai", "jam_selesai") if c not in idx]
    if missing:
        raise SystemExit(f"FAIL: kolom tidak ditemukan: {missing}. "
                         f"Header terbaca: {list(rows[0].keys())}")
    out = []
    for row in rows:
        vals = list(row.values())
        out.append({c: str(vals[i]).strip() for c, i in idx.items() if i < len(vals)})
    return out


def main():
    argv = sys.argv[1:]
    tab, kind_flag = "Sheet1", None
    if "--sheet" in argv:
        i = argv.index("--sheet")
        tab, kind_flag = argv[i + 1], "sheet"
        del argv[i:i + 2]
    if "--kind" in argv:
        i = argv.index("--kind")
        kind_flag = argv[i + 1]
        del argv[i:i + 2]

    cfg = json.loads(DRIVE_CFG.read_text()) if DRIVE_CFG.exists() else {}
    if argv:
        file_id = [a for a in argv if not a.startswith("--")][0]
        kind = kind_flag or "auto"
        cfg = {"fileId": file_id, "kind": kind, "tab": tab}
        DATA.mkdir(parents=True, exist_ok=True)
        DRIVE_CFG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    elif cfg.get("fileId"):
        file_id = cfg["fileId"]
        kind = kind_flag or cfg.get("kind", "auto")
        tab = cfg.get("tab", tab)
    else:
        raise SystemExit("FAIL: beri fileId Google Drive sebagai argumen, "
                         "mis. python3 tools/fetch-drive-jadwal.py 1AbC...xyz")

    h = load_helpers()
    if kind == "sheet":
        try:
            rows = values_to_rows(read_sheet_via_api(file_id, tab), h)
        except SystemExit as e:
            first = str(e).splitlines()[0][:90]
            print(f"⚠️  Sheets API tidak bisa dipakai ({first})\n"
                  f"    -> dialihkan ke ekspor Drive (hasil sama).")
            rows = csv_text_to_rows(read_csv_file(file_id), h)
    else:
        rows = csv_text_to_rows(read_csv_file(file_id), h)

    out, warn, ditolak = [], [], []
    for row in rows:
        poli, dokter = row.get("poli", ""), row.get("dokter", "")
        if not (poli and dokter):
            continue
        jam_m, jam_s = h.norm_jam(row.get("jam_mulai")), h.norm_jam(row.get("jam_selesai"))
        if not (jam_m and jam_s):
            warn.append(f"  - jam tidak valid: '{dokter}' / {row.get('hari')} "
                        f"({row.get('jam_mulai')} - {row.get('jam_selesai')})")
            continue
        hari_list = h.expand_hari(row.get("hari"))
        if not hari_list:
            ditolak.append(f"  - {dokter} | hari terbaca: {row.get('hari')!r}")
            continue
        for hari in hari_list:
            out.append({"poli": poli, "dokter": dokter,
                        "spesialisasi": row.get("spesialisasi", ""),
                        "hari": hari, "jam_mulai": jam_m, "jam_selesai": jam_s,
                        "sumber": "praktek"})

    if ditolak:
        raise SystemExit(
            "FAIL: ada baris dengan kolom HARI yang tidak dikenali — "
            "tidak ada perubahan yang ditulis (supaya jadwal tidak salah tayang):\n"
            + "\n".join(ditolak)
            + "\n  Format hari yang benar: Senin | Senin - Jumat | Senin, Rabu, Jumat"
              " | Setiap hari | Hari kerja")
    if not out:
        raise SystemExit("FAIL: tidak ada baris jadwal valid.")

    DATA.mkdir(parents=True, exist_ok=True)
    fields = ["poli", "dokter", "spesialisasi", "hari", "jam_mulai", "jam_selesai", "sumber"]
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)

    print(f"✅ {len(out)} baris jadwal dari Drive ({kind}: {file_id}) -> {CSV_OUT.name}")
    if warn:
        print("⚠️  peringatan:")
        print("\n".join(warn))
    subprocess.run([sys.executable, str(BUILD)], check=True)


if __name__ == "__main__":
    main()
