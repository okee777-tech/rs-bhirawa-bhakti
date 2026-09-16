#!/usr/bin/env bash
# Update jadwal dokter di website RS Bhirawa Bhakti.
#
# Alur:  Google Sheet (Drive)  ->  data/jadwal-dokter.csv  ->  dokter.html  ->  Netlify
#
# Pakai: ./update-jadwal.sh
#   1) Staf edit jadwal di Google Sheet "JADWAL DOKTER (Website)".
#   2) Jalankan script ini. Selesai.
set -euo pipefail
cd "$(dirname "$0")"

echo "▶ 1/3  Ambil jadwal terbaru dari Google Drive…"
python3 tools/fetch-drive-jadwal.py

echo
echo "▶ 2/3  Cek hasilnya cocok dengan data sumber…"
python3 tools/banding-jadwal.py | tail -3

echo
# Hanya berkas situs yang diunggah (scripts & data tidak ikut ke publik)
DIST="dist"
rm -rf "$DIST"
mkdir -p "$DIST/assets"
cp ./*.html "$DIST"/
cp assets/style.css assets/main.js assets/logo.png "$DIST/assets"/
echo "▶ 3/3  Kirim ke Netlify (folder $DIST)…"
if command -v netlify >/dev/null 2>&1; then
  netlify deploy --prod --dir "$DIST"
elif command -v npx >/dev/null 2>&1; then
  echo "    (netlify CLI belum terpasang — mencoba lewat npx)"
  npx --yes netlify-cli deploy --prod --dir "$DIST"
else
  echo "    ⚠️  Netlify CLI tidak ada. Unggah isi folder $DIST ke Netlify."
  exit 0
fi
echo
echo "✅ Selesai. Cek https://rsbhirawabhaktimalang.netlify.app/dokter.html"
