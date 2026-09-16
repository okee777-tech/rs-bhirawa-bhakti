# Dokumentasi Struktural — Website RS Bhirawa Bhakti

> **Terakhir diperbarui:** 16 September 2026
> **Lokasi proyek:** `/home/rega/Workspace/Halaman_RS BHirawa Bhakti`
> **Situs live:** https://rsbhirawabhaktimalang.netlify.app
>
> Dokumen ini menjelaskan **bagaimana sistem ini tersusun dan bekerja**. Kalau ada
> perubahan struktur, perbarui dokumen ini — bukan hanya script-nya.

---

## 1. Tujuan & Prinsip

Website profil RS Bhirawa Bhakti berbentuk **HTML statis murni**. Yang dinamis hanya satu:
**jadwal praktek dokter**, karena datanya sering berubah.

Prinsip yang dipegang:

| Prinsip | Konsekuensi teknis |
|---|---|
| Jadwal harus mudah diperbarui staf non-teknis | Sumber data = **Google Sheet**, bukan file di komputer |
| Situs harus tetap cepat & SEO-aman | Jadwal **dicetak jadi HTML statis** saat build, bukan diambil saat halaman dibuka |
| Tidak boleh salah tayang | Baris bermasalah **menolak seluruh update**, bukan dilewati diam-diam |
| Data privat tidak boleh bocor | NIK, nomor HP, nomor SIP dokter **tidak pernah** masuk ke output mana pun |

**Keputusan desain yang pernah dibandingkan** (jangan diulang tanpa alasan baru):

- ❌ *Runtime fetch* (halaman mengambil data Google saat dibuka) — ditolak: bergantung Google saat pengunjung membuka, dan konten tidak terbaca mesin pencari.
- ❌ *WordPress* — ditolak untuk tahap ini: butuh hosting berbayar + pemeliharaan rutin, padahal kebutuhan masih informasional.
- ✅ *Build-time static* — dipilih: sumber mudah diedit, hasil tetap HTML statis.

---

## 2. Alur Data (satu arah)

```
┌─────────────────────────────┐
│ Google Sheet                │   staf RS edit di browser
│ "JADWAL DOKTER (Website)"   │   (folder Drive: Website)
└──────────────┬──────────────┘
               │  gog drive download  →  ekspor otomatis ke CSV
               │  (Drive API; Sheets API TIDAK dipakai/tidak aktif)
               ▼
┌─────────────────────────────┐
│ tools/fetch-drive-jadwal.py │   validasi kolom, hari, jam
│                             │   TOLAK kalau ada hari tak dikenali
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ data/jadwal-dokter.csv      │   bentuk kanonik (1 baris = 1 dokter-hari)
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ tools/build-jadwal.py       │   cetak tabel HTML (grup hari + rowspan)
│                             │   tulis di antara penanda JADWAL:MULAI/SELESAI
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ dokter.html                 │  ← hanya file ini yang berubah
└──────────────┬──────────────┘
               │  staging: dist/ (html + assets saja)
               ▼
┌─────────────────────────────┐
│ Netlify (production)        │  https://rsbhirawabhaktimalang.netlify.app
└─────────────────────────────┘
```

Penggerak otomatisnya: job `auto-jadwal-dokter` (lihat §8) → menjalankan
`tools/auto-update-jadwal.sh` yang melakukan seluruh rantai di atas.

**Tidak ada data yang mengalir balik** dari website ke Sheet. Situs hanya menerima.

---

## 3. Peta Berkas

### Berkas situs (yang tayang ke publik)

| Berkas | Isi |
|---|---|
| `index.html` | Beranda (layanan, dokter, artikel, kontak) |
| `dokter.html` | **Halaman dinamis** — isi tabel jadwal digenerate |
| `komplain.html` | Alur pengaduan, tombol WhatsApp |
| `kontak.html` | Alamat, telepon, peta |
| `assets/style.css` | Seluruh tampilan |
| `assets/main.js` | Menu mobile + placeholder pemilih bahasa |
| `assets/logo.png` | Logo RS |

### Skrip (tidak pernah tayang ke publik)

| Skrip | Peran |
|---|---|
| `tools/fetch-drive-jadwal.py` | **Jalur utama.** Ambil Sheet dari Drive → validasi → `data/jadwal-dokter.csv` → panggil `build-jadwal.py` |
| `tools/build-jadwal.py` | Cetak blok HTML jadwal ke `dokter.html` di antara penanda |
| `tools/cek-jadwal-drive.sh` | Bandingkan sidik jari (sha256) data Sheet vs deploy terakhir → cetak `CHANGED`/`SAME`/`FAIL` |
| `tools/auto-update-jadwal.sh` | Rantai penuh tanpa manusia: fetch → verifikasi → staging `dist/` → deploy Netlify → simpan hash |
| `tools/banding-jadwal.py` | Uji silang: tabel di `dokter.html` vs data sumber. Alat pembuktian utama |
| `tools/extract-jadwal.py` | **Jalur lama/sekunder.** Ambil dari xlsx HFIS BPJS lokal (lihat §4) |
| `tools/fetch-google-sheet.py` | **Jalur alternatif.** Ambil dari URL "Publish to web" Google Sheet. Juga sumber fungsi normalisasi hari/jam yang dipakai bersama |
| `update-jadwal.sh` | Untuk manusia: fetch → verifikasi → deploy (satu perintah) |

### Data kerja

| Berkas | Fungsi |
|---|---|
| `data/drive-source.json` | `{fileId, kind, tab}` — ID Sheet yang dibaca. **Ini yang menentukan sumber data** |
| `data/jadwal-dokter.csv` | Bentuk kanonik hasil olahan (7 kolom, termasuk `sumber`) |
| `data/.last-deployed.sha256` | Sidik jari data yang sudah tayang. Penggerak deteksi perubahan |
| `dist/` | Staging deploy. **Hasil generate — jangan diedit manual** |

---

## 4. Sumber Data

### Sumber aktif: Google Sheet

| | |
|---|---|
| Nama | `JADWAL DOKTER (Website)` |
| ID | `15YK-5m6Xti6ZtLVNbwR6qb6wmPUeso7As2MQtW6k_Dg` |
| Lokasi | Google Drive → folder **Website** (`1MxGwhKV1cZy_LiZyjGi_HQUgWC2mW-zh`) |
| Pemilik | `casemixrsbbmalang@gmail.com` |
| Akses alat | `gog` (CLI Google Workspace) dengan akun yang sama, scope `drive,sheets` |
| Dibaca | `kind: "auto"` → diekspor otomatis jadi CSV via Drive API |

**Kolom (nama header ini yang dibaca — jangan diubah):**

| Kolom | Wajib | Keterangan |
|---|---|---|
| `Poli` | ya | Nama poli, mis. `Poli Anak` |
| `Dokter` | ya | Nama + gelar, mis. `dr. Meisyarah Khairani, Sp.A` |
| `Spesialisasi` | tidak | Hanya dipakai poli gigi, mis. `Bedah Mulut` |
| `Hari` | ya | Lihat tabel format di bawah |
| `Jam Mulai` | ya | `15.00` atau `15:00` |
| `Jam Selesai` | ya | `18.00` atau `18:00` |

**Format kolom `Hari` yang diterima** (fungsi `expand_hari` di `fetch-google-sheet.py`):

| Ditulis | Hasil |
|---|---|
| `Senin` | 1 hari |
| `Senin - Jumat` | 5 hari berurutan |
| `Senin, Rabu, Jumat` | 3 hari |
| `Senin/Rabu`, `Senin dan Rabu` | 2 hari |
| `Setiap hari` | 7 hari |
| `Hari kerja` | Senin–Jumat |

Hari yang tidak dikenali → **seluruh proses ditolak** dengan pesan `FAIL` + daftar
baris bermasalah. Tidak ada partial write. Aturan ini sengaja keras: lebih baik
jadwal tidak ter-update daripada ter-update salah.

### Sumber sekunder: xlsx HFIS BPJS (arsip)

`/home/rega/Workspace/Logo/JADWAL DOKTER SESUAI HFIS BPJS.xlsx` — 17 sheet (1 per poli).

| | |
|---|---|
| Kolom `J:K` | **Jam kerja** — jadwal internal (BUKAN untuk publik) |
| Kolom `L:M` | **Praktek Poli Non Eksekutif** — inilah jadwal yang tayang ke pasien |

Diproses oleh `tools/extract-jadwal.py`. Sumber ini yang **di-cocokkan 100%** dengan
website saat migrasi awal (17 dokter-poli, 0 selisih).

⚠️ **Berkas ini memuat NIK, nomor HP, dan nomor SIP dokter.** Karena itu ekstraktornya
hanya mengambil `nama`, `hari`, `jam` — tidak ada kolom privat yang ikut ke output.

Poli yang isinya hanya kolom "Jam kerja" (**Anastesi**, **Radiologi**) **tidak
ditampilkan** di website: itu jadwal jaga, bukan jadwal poli. Filter teknisnya:
hanya baris dengan `sumber == "praktek"` yang dicetak oleh `build-jadwal.py`.

Sheet lain yang kosong/hanya kerangka: `DOKTER UMUM`, `DOKTER GIGI UMUM`, `ORTOPHEDIA`, `Mata`.

---

## 5. Struktur `dokter.html` (bagian yang digenerate)

Isi tabel jadwal ditulis **hanya** di antara dua penanda:

```html
<!-- JADWAL:MULAI -->
… 8 blok poli, tiap blok: <h2 class="poli-title"> + <div class="table-wrap"> + <table class="schedule"> …
<!-- JADWAL:SELESAI -->
```

Di luar penanda itu (`dokter.html`) berisi header, footer, catatan sumber data, dan
disclaimer. **`build-jadwal.py` tidak menyentuh bagian luar penanda.**

Bentuk tiap blok:

```html
<h2 class="poli-title">👶 Poli Anak</h2>
<div class="table-wrap">
  <table class="schedule">
    <thead><tr><th>Dokter</th><th>Hari</th><th>Jam</th></tr></thead>
    <tbody>
      <tr><td rowspan="2"><strong>dr. Fiona Paramitha, Sp.A</strong></td>
          <td>Senin – Jumat</td><td>06.45 – 08.45</td></tr>
      <tr><td>Sabtu</td><td>07.00 – 09.00</td></tr>
    </tbody>
  </table>
</div>
```

Aturan pencetakan yang berlaku (semuanya di `build-jadwal.py`):

1. **Urutan poli** tetap: Anak 👶 · Bedah 🔪 · Kandungan (Obgyn) 🤰 · Penyakit Dalam 🩺 · Jantung ❤️ · Saraf 🧠 · THT-KL 👂 · Gigi Spesialis 🦷. Poli baru masuk paling bawah dengan ikon 🏥.
2. **Satu dokter satu `rowspan`** — semua slot dokter itu digabung dalam satu sel nama.
3. **Hari dengan jam sama digabung** menjadi satu baris, urut hari (mis. `Selasa, Kamis`).
4. **Rentang diringkas** kalau ≥3 hari berurutan → `Senin – Jumat`. Kalau tidak berurutan, ditulis daftar.
5. **Kolom `Spesialisasi` muncul otomatis** hanya kalau ada poli yang memakainya (yaitu poli gigi). Jadi tabel poli lain tetap 3 kolom.
6. Nama dokter dirapikan: spasi/koma, awalan `dr.`/`drg.`, *Title Case*, dan gelar
   spesialis dibakukan (`Sp. OG` → `Sp.OG`, `Sp S.` → `Sp.S`, `M.biomed` → `M.Biomed`).
   Fungsi `clean_nama` idempoten — aman dijalankan berulang.

**Menambah poli baru atau mengganti ikon** = ubah daftar `POLI_ORDER` di `build-jadwal.py`.

---

## 6. Cara Menjalankan

### Untuk staf RS (mengubah jadwal)

Buka Sheet → ubah → selesai. Maksimal 1 jam kemudian situs menyesuaikan sendiri
(dijalankan job `auto-jadwal-dokter`). Laporan singkat dikirim ke chat.

### Untuk operator (di komputer ini)

```bash
cd "/home/rega/Workspace/Halaman_RS BHirawa Bhakti"

./update-jadwal.sh                  # ambil data terbaru + verifikasi + deploy
python3 tools/fetch-drive-jadwal.py # hanya ambil & bangun ulang HTML (tanpa deploy)
python3 tools/banding-jadwal.py     # cek tabel HTML vs data sumber
bash tools/cek-jadwal-drive.sh      # CHANGED / SAME / FAIL
```

Urutan bebas dijalankan berulang — seluruh rantai **idempoten** (dijalankan dua kali,
hasilnya sama, `dokter.html` tidak berubah).

### Prasyarat yang harus hidup

| Alat | Lokasi | Kegunaan |
|---|---|---|
| `gog` | `~/.local/bin/gog` | Baca Drive/Sheet |
| `netlify` | `~/.local/bin/netlify` | Deploy ke Netlify |
| `python3` + `openpyxl` | sistem | Olah data & cetak HTML |

---

## 7. Deploy (Netlify)

| | |
|---|---|
| Situs | `rsbhirawabhaktimalang` (ID `b80d5197-39b0-4721-9ac1-39f7afdf7d26`) |
| Akun | `casemixrsbbmalang@gmail.com` (Aditya Rega Pradikma) — cek dengan `netlify status` |
| Cara deploy | `netlify deploy --prod --dir dist` |
| Isi `dist/` | Hanya `*.html` + `assets/` — supaya skrip & data tidak ikut terunggah |
| Rollback | Riwayat deploy tersimpan di Netlify; rollback tanpa kehilangan data |

Catatan penting:

- Situs ini **tidak tersambung ke Git** (`build_settings.repo_url: null`), jadi tidak
  ada build otomatis di sisi Netlify. Build terjadi di komputer ini lalu file diunggah.
- **Deploy preview (draft) dilindungi SSO** → URL preview membalas `401` bila dibuka
  tanpa login. Ini normal, bukan kerusakan. Yang production tetap publik.
- Fitur **Pretty URLs** Netlify aktif, jadi `/dokter` dan `/dokter.html` dua-duanya jalan.
- Kalau Netlify CLI di pasang ulang: `npm install -g netlify-cli --prefix "$HOME/.local"`
  (npm sistem milik `/usr/lib` butuh root, jadi prefix user dipakai).

---

## 8. Otomasi

Dua job di Gateway. Keduanya menulis hasilnya ke sesi chat yang sama.

### a. `auto-jadwal-dokter` — update otomatis

| | |
|---|---|
| ID | `25ad2b3c-c1cf-4d9f-9975-5fe323af7ac6` |
| Jadwal | `0 * * * *` (tiap jam, zona `Asia/Jakarta`) |
| Pemicu | Script cek: unduh Sheet → sha256 → bandingkan `data/.last-deployed.sha256` → **menyala hanya kalau berubah** |
| Aksi | Jalankan `tools/auto-update-jadwal.sh` lalu lapor singkat |
| Kalau tidak berubah | Diam total — tidak ada deploy, tidak ada notifikasi |

### b. `cek-drive-jadwal-dokter` — alarm kesehatan akses

| | |
|---|---|
| ID | `a900c113-fae1-40c5-8968-0e5b058bd1b6` |
| Jadwal | `0 7 * * *` (tiap 07:00 WIB) |
| Pemicu | Cek apakah `gog` masih bisa membaca Sheet |
| Aksi | Hanya kalau **gagal**: beri tahu Rega + perintah perbaikannya (maksimal sekali per 24 jam) |

**Kenapa dipisah:** satu menjaga kesegaran data, satu menjaga kesehatan akses.
Kalau token Google mati, alarm akan berbunyi sebelum ada orang yang bingung
kenapa jadwal tidak bisa diperbarui.

---

## 9. Penanganan Masalah

| Gejala | Penyebab | Tindakan |
|---|---|---|
| `FAIL: akses Google Drive sudah tidak berlaku (token mati)` | Refresh token Google dicabut/kedaluwarsa | `gog auth add casemixrsbbmalang@gmail.com --services drive,sheets --force-consent` lalu klik **Allow** di browser |
| `Sheets API is not enabled for this OAuth project` | Sheets API belum diaktifkan di project `202431686428` | Tidak perlu selama memakai mode `auto` (Drive API yang dipakai). Hanya perlu kalau ingin **menulis** ke Sheet dari script |
| `FAIL: ada baris dengan kolom HARI yang tidak dikenali` | Salah ketik hari, atau format baru | Perbaiki di Sheet. Format yang benar ada di §4 |
| `FAIL: kolom tidak ditemukan: [...]` | Nama header kolom diubah/terhapus | Kembalikan nama header seperti §4 |
| Deploy preview membalas `401` | Proteksi SSO Netlify untuk non-production | Normal — pakai URL production |
| `EACCES: mkdir '/usr/lib/node_modules/...'` | `npm` sistem butuh root | Pakai `--prefix "$HOME/.local"` |
| Situs tidak ikut berubah padahal Sheet sudah diedit | Komputer mati (otomasi tidak jalan), atau data identik | Jalankan `./update-jadwal.sh` manual; cek `bash tools/cek-jadwal-drive.sh` |

**Otorisasi Google:** token bisa hangus kalau OAuth consent screen kembali berstatus
*Testing* (Google mencabut refresh token tiap 7 hari). Sekarang sudah **In production**
(project `202431686428`), dan token terakhir diterbitkan 16 Sep 2026 pukul 19:03 WIB.
Kalau perlu otorisasi ulang, prosesnya membuka browser di komputer ini — tautan/kode
otorisasi **tidak boleh** ditempel ke chat.

---

## 10. Batasan & Risiko yang Diketahui

1. **Otomasi berjalan di komputer ini.** Kalau komputer mati, tidak ada pengecekan;
   jadwal baru tersinkron saat komputer hidup lagi. Untuk benar-benar lepas dari
   komputer, perlu repo GitHub + build di sisi Netlify (GitHub belum tersambung ke agen).
2. **Sudah terpakai:** 8 poli · 17 dokter · 58 slot jadwal (kondisi 16 Sep 2026).
3. **Foto dokter belum ada** — halaman masih menyebut "foto menyusul".
4. **Versi bahasa Inggris** baru placeholder di menu (belum berfungsi).
5. Sumber xlsx HFIS tetap menjadi **rujukan resmi RS** untuk jadwal; Sheet "Website"
   adalah turunannya. Kalau berubah, sebaiknya keduanya disamakan — `banding-jadwal.py`
   bisa dipakai untuk memeriksa selisih.

---

## 11. Sejarah Keputusan Singkat

| Tanggal | Keputusan |
|---|---|
| 16 Sep 2026 | Situs statis diunggah ke Netlify (oleh pemilik, lewat Netlify) |
| 16 Sep 2026 | Sumber jadwal dipilih: **Sheets + build statis** (bukan runtime fetch, bukan WordPress) |
| 16 Sep 2026 | Jadwal dari xlsx HFIS divalidasi: 17 dokter-poli **identik** dengan tabel website |
| 16 Sep 2026 | Sumber pindah ke Google Sheet di folder Drive **Website**; `gog` diotorisasi ulang |
| 16 Sep 2026 | OAuth app dipindah ke **In production**; token diterbitkan ulang agar tidak hangus 7 hari |
| 16 Sep 2026 | Versi rapi menggantikan versi lama di production (deploy manual pertama lewat CLI) |
| 16 Sep 2026 | Otomasi per jam + alarm token harian dipasang dan **diuji end-to-end** |
| 16 Sep 2026 | Parsing hari diperkuat; baris bermasalah kini menolak seluruh update |

---

## 12. Ringkasan Satu Paragraf

Staf RS mengedit Google Sheet `JADWAL DOKTER (Website)` di folder Drive **Website**.
`tools/fetch-drive-jadwal.py` membacanya lewat `gog` (ekspor CSV via Drive API),
memvalidasi hari & jam, dan menulis `data/jadwal-dokter.csv`. `tools/build-jadwal.py`
mencetak tabel HTML ke `dokter.html` di antara penanda `JADWAL:MULAI/SELESAI`, dengan
aturan pengelompokan hari dan `rowspan` per dokter. `tools/auto-update-jadwal.sh`
menyalin berkas situs ke `dist/` lalu mengunggahnya ke Netlify. Semua ini berjalan
otomatis tiap jam lewat job `auto-jadwal-dokter` — yang hanya bergerak kalau sidik
jari data berubah — dan dijaga oleh job `cek-drive-jadwal-dokter` yang berbunyi
kalau akses Google mati.

---

## 13. Level 2 — Otomasi Penuh (GitHub + Netlify Build Hook)

Membuat situs update **sendiri tanpa komputer ini**. Level 1 (§8) masih butuh komputer
ini hidup + `gog`. Level 2 memindahkan build ke server Netlify: tidak ada polling lokal,
tidak ada ketergantungan token Google di mesin ini.

**Arsitektur:**

```
Google Sheet ──(staf edit)──▶ Apps Script (onEdit → penjadwal 5 mnt) ──▶ Netlify Build Hook
                                                                              │
                                                                              ▼
                          Netlify build: clone repo GitHub → fetch CSV publik → build → live
```

**Berkas baru:**

| Berkas | Peran |
|---|---|
| `netlify.toml` | Build command + publish dir untuk Netlify (dibaca saat tersambung Git) |
| `tools/netlify-build.sh` | Build di server: fetch CSV publik → build → staging `dist/` |
| `google-apps-script/Code.gs` | Pemicu: edit Sheet → trigger Netlify (≤5 menit) |

**Prasyarat (butuh akun pemilik):**

1. Akun **GitHub** + satu repository untuk folder ini.
2. Situs Netlify disambungkan ke repo itu (Build & deploy → Continuous deployment →
   Connect to Git).
3. Google Sheet di-*publish* ke web (File → Share → Publish to web → format CSV) → URL
   publiknya disimpan sebagai environment variable `SHEET_CSV_URL` di Netlify.
4. Satu **Build Hook** dibuat di Netlify (Build & deploy → Build hooks) → URL-nya
   ditempel ke Apps Script lewat `setHook(...)`.

**Langkah setup ringkas:**

1. Buat repo GitHub, push folder ini (`dist/`, `data/`, `.netlify/` otomatis dikecualikan
   oleh `.gitignore`).
2. Netlify → sambungkan ke repo → build command & publish dir terbaca otomatis dari
   `netlify.toml`.
3. Sheet → Publish to web → CSV → salin URL.
4. Netlify → Environment → `SHEET_CSV_URL` = URL tadi.
5. Netlify → Build hooks → Add → salin URL hook.
6. Sheet → Ekstensi → Apps Script → tempel `Code.gs` → jalankan `setHook(URL)` lalu
   `setup()` → izinkan akses.
7. Tes: edit satu sel → ≤5 menit situs ter-update sendiri.

Catatan: build di server memakai `fetch-google-sheet.py` (URL publik) — **bukan** `gog`.
Jadi mode ini tidak butuh token Google di komputer ini. Mode Level 1 tetap bisa dipakai
sebagai cadangan.
