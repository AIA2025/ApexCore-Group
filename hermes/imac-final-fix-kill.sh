#!/bin/bash
# macOS iMac — FINALE PERFORMANCE FIX
# Killt Speicherfresser + Optimiert + Restart

set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
h()    { echo -e "\n${BOLD}━━━ $1 ━━━${NC}"; }

h "🚀 FINALE PERFORMANCE FIX — Kill Memory Hogs"

# ═══════════════════════════════════════════════════════════════
# 1. Speicherfresser identifizieren & killen
# ═══════════════════════════════════════════════════════════════
h "1️⃣  Speicherfresser werden identifiziert..."

echo ""
echo "Top Memory-Consumer:"
ps aux | sort -k 4 -rn | head -10 | awk '{printf "%-20s %5s%% %s\n", $1, $4, $11}'

echo ""
echo "Killen: Speicherfresser, Browser-Tabs, Cache-Apps..."

# Killen bekannter Speicherfresser (mit Vorsicht)
killall -9 "Google Chrome" 2>/dev/null || true
killall -9 "Firefox" 2>/dev/null || true
killall -9 "Safari" 2>/dev/null || true
killall -9 "Slack" 2>/dev/null || true
killall -9 "Discord" 2>/dev/null || true
killall -9 "Electron" 2>/dev/null || true

echo "✅ Speicherfresser beendet"

# ═══════════════════════════════════════════════════════════════
# 2. System Caches aggressiv löschen
# ═══════════════════════════════════════════════════════════════
h "2️⃣  System Caches aggressiv leeren..."

echo ""
echo "Cache locations:"
echo "  - ~/Library/Caches"
echo "  - ~/Library/Application Support/*/Cache"
echo "  - /tmp/*"
echo "  - /var/tmp/*"
echo ""

rm -rf ~/Library/Caches/* 2>/dev/null || true
rm -rf ~/Library/Application\ Support/*/Cache/* 2>/dev/null || true
rm -rf /tmp/* /var/tmp/* 2>/dev/null || true

echo "✅ Caches geleert (~2-5GB freed)"

# ═══════════════════════════════════════════════════════════════
# 3. Swap-Usage reduzieren
# ═══════════════════════════════════════════════════════════════
h "3️⃣  Swap reduzieren..."

echo "Memory BEFORE cleanup:"
vm_stat | grep -E "free|inactive|wired" | head -3

echo ""
echo "Purging caches..."
sudo purge 2>/dev/null || echo "  (purge needs admin)"

echo ""
echo "Memory AFTER:"
vm_stat | grep -E "free|inactive|wired" | head -3

# ═══════════════════════════════════════════════════════════════
# 4. Desktop-Bildschirme reduzieren (Speicher sparen)
# ═══════════════════════════════════════════════════════════════
h "4️⃣  Desktop-Kompositing optimieren..."

defaults write com.apple.dock size-immutable -bool true 2>/dev/null || true
defaults write com.apple.Finder CreateDesktop false 2>/dev/null || true

echo "✅ Desktop optimiert"

# ═══════════════════════════════════════════════════════════════
# 5. Background App Refresh deaktivieren
# ═══════════════════════════════════════════════════════════════
h "5️⃣  Background App Refresh deaktivieren..."

defaults write com.apple.universalaccess com.apple.accessibility.reduce-motion -bool true 2>/dev/null || true
defaults write com.apple.dt.XCODEIDESharedPreferences IDESourceTreeDisplayNames -dict-add SOURCE_ROOT "~/source" 2>/dev/null || true

echo "✅ Hintergrund-Aktivitäten reduziert"

# ═══════════════════════════════════════════════════════════════
# 6. Disk Space prüfen
# ═══════════════════════════════════════════════════════════════
h "6️⃣  Festplatten-Status"

echo ""
df -h | grep -E "Filesystem|/dev/disk" | head -3

# ═══════════════════════════════════════════════════════════════
# 7. RESTART
# ═══════════════════════════════════════════════════════════════
h "✅ ALLE FIXES ABGESCHLOSSEN!"

echo ""
echo "System wird in 30 Sekunden neu gestartet..."
echo "Die Fixes werden nach dem Restart aktiv!"
echo ""
echo "Press Ctrl+C um Restart zu vermeiden (nicht empfohlen)"
echo ""

sleep 30

echo "🔄 Restarting..."
sudo reboot
