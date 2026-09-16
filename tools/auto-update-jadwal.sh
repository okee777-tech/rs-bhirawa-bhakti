#!/usr/bin/env bash
# Ambil jadwal terbaru dari Drive, bangun ulang dokter.html, deploy ke Netlify.
# Dipakai oleh otomasi terjadwal (tanpa campur tangan manusia).
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

echo "▶ ambil data terbaru dari Google Sheet…"
python3 tools/fetch-drive-jadwal.py

echo "▶ verifikasi hasil…"
python3 tools/banding-jadwal.py | tail -3

echo "▶ staging dist/ dan deploy ke Netlify…"
rm -rf dist && mkdir -p dist/assets
cp ./*.html dist/
cp assets/style.css assets/main.js assets/logo.png dist/assets/
netlify deploy --prod --dir dist --message "Auto: jadwal dokter dari Google Sheet"

bash tools/cek-jadwal-drive.sh --simpan
echo "✅ selesai"
