# TUGAS UNTUK AGENT — Perbaiki otomasi jadwal dokter (website RS Bhirawa Bhakti)

> **Dibuat:** 16 September 2026, 21:35 WIB
> **Status:** jalur GitHub Actions sudah terpasang dan **sedang gagal di langkah pertama**
> **Rujukan lengkap sistem:** `README.md` (bagian §1–§14)

---

## 1. Konteks

Website RS Bhirawa Bhakti adalah situs statis. Jadwal dokter bersumber dari Google Sheet,
lalu **dibangun ulang menjadi HTML** dan di-deploy ke Netlify. Ada dua jalur otomasi:

| Jalur | Status | Keterangan |
|---|---|---|
| **Level 1** — job lokal di gateway (`auto-jadwal-dokter`, tiap jam) | ✅ jalan & terbukti | butuh komputer ini hidup |
| **Level 2** — GitHub Actions (tiap 10 menit) | ⚠️ **terpasang tapi GAGAL** | inilah yang harus diperbaiki |

Tujuan Level 2: situs ter-update **tanpa komputer lokal**. Jalur Netlify Build Hook
(§13 README) sudah **tidak dipakai** — jangan dikerjakan.

---

## 2. Lokasi & identitas

| Item | Nilai |
|---|---|
| Folder proyek | `/home/rega/Workspace/Halaman_RS BHirawa Bhakti` |
| Repo GitHub | `git@github.com:okee777-tech/rs-bhirawa-bhakti.git` (branch `main`, **publik**) |
| Workflow | `.github/workflows/deploy-jadwal.yml` (state: `active`) |
| Situs | https://rsbhirawabhaktimalang.netlify.app |
| Netlify site id | `b80d5197-39b0-4721-9ac1-39f7afdf7d26` (sudah tertanam di workflow) |
| Sheet sumber | `JADWAL DOKTER (Website)` — ID `15YK-5m6Xti6ZtLVNbwR6qb6wmPUeso7As2MQtW6k_Dg` |
| Folder Drive | `Website` |

---

## 3. MASALAH UTAMA (P0) — yang harus diperbaiki

Workflow gagal di langkah **"Ambil jadwal dari Google Sheet & bandingkan sidik jari"**.

**Bukti** (berkas `STATUS.txt` di repo, ditulis otomatis oleh workflow saat gagal):

```
alasan_awal: tidak-kosong        ← variable SHEET_CSV_URL SUDAH terisi
panjang_url: 135
pola_url: google                 ← alamatnya memang Google
berkolom_poli: tidak             ← ❌ isi unduhan BUKAN CSV jadwal
```

**Diagnosis:** nilai `SHEET_CSV_URL` bukan URL "Publish to web", sehingga yang terunduh
bukan CSV (kemungkinan halaman HTML/login). Akibatnya workflow berhenti sebelum build —
situs tidak terpengaruh, tidak ada deploy salah.

**Bukti tambahan yang belum sempat terekam:** pada run #3, berkas `STATUS.txt` versi baru
(tambahan `kode_http`, `content_type`, `ada_d_e`, `akhiran_url`) **tidak ter-push** karena
terjadi bentrok push. Perlu commit/rebase agar terbaru.

### Cara memperbaiki

1. Buka Sheet `JADWAL DOKTER (Website)`.
2. **File → Share → Publish to web**.
3. Kotak 1: pilih tab jadwalnya. Kotak 2: pilih **Comma-separated values (.csv)**.
4. Klik **Publish**, lalu **salin URL yang baru muncul**.
   - URL benar berbentuk: `https://docs.google.com/spreadsheets/d/` **`e/`** `2PACX-…/pub?output=csv`
   - URL salah (dari menu Share biasa): `../spreadsheets/d/15YK-…/edit?usp=sharing`
5. Perbarui variable `SHEET_CSV_URL` di
   `https://github.com/okee777-tech/rs-bhirawa-bhakti/settings/variables/actions`
   (boleh juga disimpan sebagai **secret** — workflow menerima keduanya).
6. **Verifikasi sebelum selesai:** buka URL itu di jendela **incognito** (tanpa login Google).
   Kalau langsung terunduh berkas `.csv`, berarti benar.

**Kriteria lolos:** baris pertama CSV memuat kata `Poli`.

---

## 4. MASALAH BELUM TERVERIFIKASI (P1)

| Item | Status |
|---|---|
| Secret `NETLIFY_AUTH_TOKEN` | **belum terbukti** — build belum pernah sampai langkah deploy. Isi secret tidak bisa dibaca siapa pun; buktinya hanya run yang sukses. |
| Variable/secret `SHEET_CSV_URL` | terbukti ada, tapi nilainya salah bentuk (lihat §3) |

Kalau deploy nanti gagal dengan pesan `secret NETLIFY_AUTH_TOKEN belum diisi`,
buat token baru: Netlify → **User settings → Applications → Personal access tokens**
(<https://app.netlify.com/user/applications#personal-access-tokens>) → salin →
simpan sebagai secret di `.../settings/secrets/actions`.

---

## 5. Cara menjalankan & memantau

**Memicu:** setiap push ke `main`, atau tiap 10 menit otomatis, atau manual:
`https://github.com/okee777-tech/rs-bhirawa-bhakti/actions/workflows/deploy-jadwal.yml` → **Run workflow**.

**Memantau tanpa login** (log GitHub butuh login, jadi pakai ini):

```bash
# status run terakhir
curl -s "https://api.github.com/repos/okee777-tech/rs-bhirawa-bhakti/actions/runs?per_page=3" \
  | python3 -c "import sys,json; [print(r['run_number'], r['created_at'], r['status'], r['conclusion'], r['id']) for r in json.load(sys.stdin)['workflow_runs']]"

# langkah mana yang gagal (untuk run id tertentu)
curl -s "https://api.github.com/repos/okee777-tech/rs-bhirawa-bhakti/actions/runs/<RUN_ID>/jobs" \
  | python3 -c "import sys,json; [print(s.get('conclusion'), s['name']) for j in json.load(sys.stdin)['jobs'] for s in j['steps']]"

# sebab kegagalan (ditulis sendiri oleh workflow — ini pengganti log)
curl -s "https://raw.githubusercontent.com/okee777-tech/rs-bhirawa-bhakti/main/STATUS.txt"

# cek situs
curl -s -o /dev/null -w "%{http_code}\n" https://rsbhirawabhaktimalang.netlify.app/dokter.html
```

**Kalau push ditolak** (`non-fast-forward`): bot kadang men-commit `STATUS.txt` /
`.jadwal-terakhir` / `dokter.html`. Jalankan `git pull --rebase origin main` lalu push lagi.

---

## 6. Alur yang benar (ringkas)

```
Google Sheet (Publish to web → CSV)
        │  tiap 10 menit
        ▼
GitHub Actions  ── unduh CSV ── bandingkan sha256 dengan berkas .jadwal-terakhir
        │                                   │
        │ sama ─────────────────────────────┘  (berhenti, tidak deploy)
        ▼ beda
tools/fetch-google-sheet.py  →  dokter.html  →  dist/  →  netlify deploy --prod
        │
        ▼
commit .jadwal-terakhir + dokter.html  (pesan memuat [skip ci] supaya tidak memicu loop)
```

---

## 7. ATURAN — jangan dilanggar

1. **Jangan pernah** menaruh kredensial (token Netlify, URL build hook, kunci apa pun) di
   repo, commit, chat, atau command line. Repo ini **publik**.
2. URL build hook Netlify ada di `google-apps-script/BUILD-HOOK.txt` (mode 600, sudah
   di-`.gitignore`). Jangan dipindah, jangan dicetak, jangan di-commit. Jalur build hook
   sekarang **tidak dipakai**.
3. **Jangan menambahkan kolom internal** (NIK, no HP, catatan pribadi) ke Sheet jadwal —
   Sheet ini menjadi sumber publik.
4. **Jangan mengubah nama header kolom** Sheet: `Poli`, `Dokter`, `Spesialisasi`, `Hari`,
   `Jam Mulai`, `Jam Selesai`.
5. Hari yang tidak dikenali **sengaja** membuat seluruh proses gagal (mencegah jadwal salah
   tayang). Jangan dilonggarkan tanpa alasan kuat.
6. Setelah Level 2 terbukti hijau, **nonaktifkan job lokal `auto-jadwal-dokter`** (id
   `25ad2b3c-c1cf-4d9f-9975-5fe323af7ac6`) supaya tidak ada dua penerbit. Job alarm token
   `cek-drive-jadwal-dokter` (`a900c113-fae1-40c5-8968-0e5b058bd1b6`) tetap dibiarkan aktif.
7. Jangan mengubah `NETLIFY_SITE_ID` di workflow — itu situs produksi yang sudah benar.

---

## 8. Definisi selesai (harus dibuktikan, bukan diasumsikan)

- [ ] Run workflow berstatus **success** (hijau), langkah "Deploy ke Netlify" ikut jalan
- [ ] Deploy baru muncul di Netlify dengan judul memuat `Auto (GitHub Actions)`
- [ ] `https://rsbhirawabhaktimalang.netlify.app/dokter.html` → HTTP **200**
- [ ] Uji nyata: ubah satu jam dokter di Sheet → dalam ≤10 menit situs ikut berubah
- [ ] `STATUS.txt` sudah tidak berisi catatan kegagalan baru
- [ ] Job lokal Level 1 dinonaktifkan (setelah semua di atas terpenuhi)

---

## 9. Kalau butuh konteks lebih dalam

Baca `README.md` di repo ini, terutama:

- §2 alur data · §3 peta berkas · §4 struktur kolom Sheet & format hari
- §5 struktur `dokter.html` (penanda `JADWAL:MULAI`/`JADWAL:SELESAI`, aturan rowspan & penggabungan hari)
- §9 penanganan masalah · §10 batasan yang diketahui · §14 jalur GitHub Actions (produksi)
