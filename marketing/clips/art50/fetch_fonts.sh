#!/usr/bin/env bash
# Holt die Schriften für den Art.-50-Clip.
# Beide Familien stehen unter der SIL Open Font License 1.1 und werden
# bewusst NICHT im Repo versioniert (siehe .gitignore).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fonts"
mkdir -p "$DIR"

BASE="https://raw.githubusercontent.com/google/fonts/main/ofl"

fetch() {
  local url="$1" out="$2"
  if [[ -s "$DIR/$out" ]]; then
    echo "vorhanden: $out"
    return
  fi
  curl -sSLf -o "$DIR/$out" "$url"
  echo "geladen:   $out ($(stat -c%s "$DIR/$out") Bytes)"
}

fetch "$BASE/sourceserif4/SourceSerif4%5Bopsz%2Cwght%5D.ttf"        'SourceSerif4[opsz,wght].ttf'
fetch "$BASE/sourceserif4/SourceSerif4-Italic%5Bopsz%2Cwght%5D.ttf" 'SourceSerif4-Italic[opsz,wght].ttf'
fetch "$BASE/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf"             'JetBrainsMono[wght].ttf'
