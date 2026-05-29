#!/usr/bin/env bash
# build-kit.sh — ApexCore PDF Build Pipeline
# Usage: ./build-kit.sh <product_slug>
# Example: ./build-kit.sh product_4

set -euo pipefail

PRODUCT="${1:-}"
BASE="/data/apex-core-central/output"
LOG="/var/log/apexcore-build.log"
REPO="https://raw.githubusercontent.com/AIA2025/apexcore/claude/sharp-brahmagupta-03oc5"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }
ok()  { echo "✅ $*" | tee -a "$LOG"; }
err() { echo "❌ $*" | tee -a "$LOG"; }

# ── Validate input ────────────────────────────────────────────────────────────
if [ -z "$PRODUCT" ]; then
  echo "Usage: $0 <product_slug>  (e.g. product_4)" >&2
  exit 1
fi

SRC_DIR="$BASE/$PRODUCT/markdown"
OUT_DIR="$BASE/$PRODUCT/final"
mkdir -p "$SRC_DIR" "$OUT_DIR"

# ── Check / install pandoc ────────────────────────────────────────────────────
if ! command -v pandoc &>/dev/null; then
  log "Installing pandoc..."
  apt-get update -qq && apt-get install -y -qq pandoc wkhtmltopdf || {
    err "pandoc install failed"; exit 1
  }
fi

# ── Find markdown source ──────────────────────────────────────────────────────
MD_FILE=$(ls "$SRC_DIR"/*.md 2>/dev/null | head -1)
if [ -z "$MD_FILE" ]; then
  # Try fetching from GitHub repo as fallback
  log "No local .md found — fetching from GitHub..."
  REMOTE_MD="$REPO/products/$PRODUCT/$(ls /home/user/apexcore/products/$PRODUCT/*.md 2>/dev/null | xargs basename 2>/dev/null || echo 'kit.md')"
  curl -fsSL "$REPO/products/$PRODUCT/$(basename $PRODUCT)-reporting-kit.md" \
    > "$SRC_DIR/$(basename $PRODUCT)-kit.md" 2>/dev/null || \
  curl -fsSL "$REPO/products/$PRODUCT/bitcoin-tax-reporting-kit.md" \
    > "$SRC_DIR/bitcoin-tax-reporting-kit.md" 2>/dev/null || {
    err "No .md file found in $SRC_DIR and fetch failed"; exit 1
  }
  MD_FILE=$(ls "$SRC_DIR"/*.md | head -1)
fi

SLUG=$(basename "$MD_FILE" .md)
PDF_FILE="$OUT_DIR/$SLUG.pdf"

log "Building: $MD_FILE → $PDF_FILE"

# ── Render PDF ────────────────────────────────────────────────────────────────
# Primary: wkhtmltopdf (fast, no LaTeX needed)
if command -v wkhtmltopdf &>/dev/null; then
  pandoc "$MD_FILE" \
    --pdf-engine=wkhtmltopdf \
    --toc --toc-depth=2 \
    -V margin-top=25mm -V margin-bottom=25mm \
    -V margin-left=20mm -V margin-right=20mm \
    -V fontsize=11pt -V papersize=a4 \
    -o "$PDF_FILE" 2>>"$LOG"
# Fallback: xelatex
elif command -v xelatex &>/dev/null; then
  pandoc "$MD_FILE" \
    --pdf-engine=xelatex \
    --toc --toc-depth=2 \
    -V geometry:margin=2.5cm \
    -V fontsize=11pt -V colorlinks=true \
    -o "$PDF_FILE" 2>>"$LOG"
else
  err "No PDF engine available (wkhtmltopdf or xelatex required)"
  exit 1
fi

# ── Validate ──────────────────────────────────────────────────────────────────
if [ -f "$PDF_FILE" ] && [ -s "$PDF_FILE" ]; then
  SIZE=$(du -h "$PDF_FILE" | cut -f1)
  ok "PDF created: $PDF_FILE ($SIZE)"
  log "Build complete."
else
  err "PDF build failed — check $LOG"
  exit 1
fi
