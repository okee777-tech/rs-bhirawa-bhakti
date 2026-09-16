#!/usr/bin/env bash
# Build yang dijalankan Netlify (di server, saat build hook / push terpicu).
# Tidak butuh gog, tidak butuh komputer lokal — sumbernya URL CSV publik.
set -euo pipefail
cd "$(dirname "$0")/.."

# URL CSV Google Sheet (hasil "Publish to web") dari environment Netlify.
: "${SHEET_CSV_URL:?Set env SHEET_CSV_URL di dashboard Netlify (Build & deploy -> Environment)}"

echo "▶ ambil jadwal dari Google Sheet…"
python3 tools/fetch-google-sheet.py "$SHEET_CSV_URL"

echo "▶ verifikasi…"
python3 tools/banding-jadwal.py | tail -2 || true

echo "▶ staging ke dist/ …"
rm -rf dist && mkdir -p dist/assets
cp ./*.html dist/
cp assets/style.css assets/main.js assets/logo.png dist/assets/

echo "✅ build selesai — publish dir = dist/"
