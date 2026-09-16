#!/usr/bin/env bash
# Cek apakah jadwal di Google Sheet sudah berubah sejak deploy terakhir.
# Output: "CHANGED <hash>" | "SAME <hash>" | "FAIL"
set -uo pipefail
cd "$(dirname "$0")/.."

CONF=data/drive-source.json
HASHFILE=data/.last-deployed.sha256
[ -f "$CONF" ] || { echo "FAIL"; exit 0; }
ID=$(python3 -c "import json;print(json.load(open('$CONF'))['fileId'])" 2>/dev/null) || { echo "FAIL"; exit 0; }

TMP=$(mktemp -d) || { echo "FAIL"; exit 0; }
trap 'rm -rf "$TMP"' EXIT
gog --account auto drive download "$ID" --out "$TMP" >/dev/null 2>&1 || { echo "FAIL"; exit 0; }
# Ambil file pertama hasil unduhan (apa pun namanya), SELARAS dengan
# tools/fetch-drive-jadwal.py yang memakai files[0] — bukan filter "*.csv",
# karena gog kadang mengekspor Sheet tanpa ekstensi .csv.
F=$(find "$TMP" -type f | head -1)
[ -n "$F" ] || { echo "FAIL"; exit 0; }

NEW=$(sha256sum "$F" | cut -d' ' -f1)
OLD=$(cat "$HASHFILE" 2>/dev/null || echo "-")
if [ "${1:-}" = "--simpan" ]; then
  printf '%s\n' "$NEW" > "$HASHFILE"; echo "SAVED $NEW"; exit 0
fi
if [ "$NEW" = "$OLD" ]; then echo "SAME $NEW"; else echo "CHANGED $NEW"; fi
