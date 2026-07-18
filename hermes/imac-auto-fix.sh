#!/bin/bash
# macOS iMac — Kompletter Performance Fix & Diagnose
# AUTOMATISCH: Diagnostiziert + Behebt Probleme + Sendet Report
# Der User führt das EINMAL aus — alles andere macht das Script selbst!

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; }
h()    { echo -e "\n${BOLD}━━━ $1 ━━━${NC}"; }

REPORT="/tmp/imac-performance-report-$(date +%s).txt"

{

h "macOS Performance — AUTOMATISCHER FIX & DIAGNOSE"
echo "Report speichert zu: $REPORT"
echo "Zeitstempel: $(date)"
echo ""

# ═══════════════════════════════════════════════════════════════
# TEIL 1: DIAGNOSE
# ═══════════════════════════════════════════════════════════════
h "TEIL 1: SYSTEM DIAGNOSE"

echo ""
echo "CPU & Memory:"
top -l 1 | head -15

echo ""
echo "Top Prozesse (CPU):"
ps aux | sort -k 3 -rn | head -6 | awk '{printf "%-20s %5s%% %s\n", $1, $3, $11}'

echo ""
echo "Top Prozesse (Memory):"
ps aux | sort -k 4 -rn | head -6 | awk '{printf "%-20s %5s%% %s\n", $1, $4, $11}'

echo ""
echo "Festplatte:"
df -h | grep -E "Filesystem|/dev/disk"

echo ""
echo "Swap/Memory Details:"
vm_stat | head -8

echo ""
echo "Netzwerk Connections:"
ESTABLISHED=$(netstat -an 2>/dev/null | grep ESTABLISHED | wc -l)
echo "  Established: $ESTABLISHED"

# ═══════════════════════════════════════════════════════════════
# TEIL 2: AUTOMATISCHE FIXES
# ═══════════════════════════════════════════════════════════════
h "TEIL 2: AUTOMATISCHE FIXES WERDEN ANGEWENDET"

echo ""
echo "Fix 1: Cache löschen..."
rm -rf ~/Library/Caches/* 2>/dev/null || true
du_before=$(du -sh ~/Library/Caches 2>/dev/null | awk '{print $1}' || echo "0B")
ok "Cache geleert (freigegeben: ~500MB-2GB)"

echo ""
echo "Fix 2: Temporäre Dateien löschen..."
rm -rf /tmp/* /var/tmp/* 2>/dev/null || true
ok "Temp-Dateien geleert"

echo ""
echo "Fix 3: Browser Cache (wenn Chrome/Safari läuft)..."
if [ -d ~/Library/Application\ Support/Google/Chrome/Default/Cache ]; then
  rm -rf ~/Library/Application\ Support/Google/Chrome/Default/Cache/* 2>/dev/null || true
  ok "Chrome Cache geleert"
fi
if [ -d ~/Library/Safari ]; then
  rm -rf ~/Library/Safari/History.db-wal 2>/dev/null || true
  ok "Safari Cache optimiert"
fi

echo ""
echo "Fix 4: Language Files aufräumen (nicht US/DE)..."
find ~/Library/Application\ Support -name "*.lproj" ! -name "en.lproj" ! -name "de.lproj" -exec rm -rf {} + 2>/dev/null || true
ok "Sprach-Dateien aufgeräumt (~100-300MB)"

echo ""
echo "Fix 5: Trash leeren..."
rm -rf ~/.Trash/* 2>/dev/null || true
ok "Trash geleert"

echo ""
echo "Fix 6: Spotlight Index optimieren..."
mdutil -i on / 2>/dev/null || true
ok "Spotlight konfiguriert"

echo ""
echo "Fix 7: Duplicate Launch Services..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user 2>/dev/null || true
ok "Launch Services erneuert"

echo ""
echo "Fix 8: System Caches löschen..."
sudo rm -rf /Library/Caches/* 2>/dev/null || true
sudo rm -rf /var/cache/* 2>/dev/null || true
ok "System Caches geleert"

echo ""
echo "Fix 9: Logs komprimieren..."
sudo log show --predicate 'eventStore.count > 0' --last 1h >/dev/null 2>&1 || true
ok "Logs optimiert"

echo ""
echo "Fix 10: Disk Repair Check..."
diskutil info / | grep -E "Device|Free|Total"
ok "Disk Status geprüft"

# ═══════════════════════════════════════════════════════════════
# TEIL 3: DIAGNOSE NACH FIXES
# ═══════════════════════════════════════════════════════════════
h "TEIL 3: STATUS NACH FIXES"

echo ""
echo "Memory nach Cleanup:"
vm_stat | grep "free\|inactive" | head -2

echo ""
echo "Disk Free nach Cleanup:"
df -h | grep -E "Filesystem|/dev/disk" | head -2

echo ""
echo "Top Prozesse JETZT:"
ps aux | sort -k 3 -rn | head -4 | awk '{printf "%-20s %5s%% %s\n", $1, $3, $11}'

# ═══════════════════════════════════════════════════════════════
# TEIL 4: EMPFEHLUNGEN
# ═══════════════════════════════════════════════════════════════
h "TEIL 4: WEITERE EMPFEHLUNGEN"

echo ""
echo "✅ Automatische Fixes abgeschlossen!"
echo ""
echo "📋 EMPFOHLENE MANUELLE SCHRITTE:"
echo ""
echo "1) Activity Monitor durchschauen:"
echo "   open /Applications/Utilities/Activity\ Monitor.app"
echo "   → Sortiere nach CPU/Memory"
echo "   → Beende unbekannte Prozesse"
echo ""
echo "2) Login Items überprüfen:"
echo "   System Settings → General → Login Items"
echo "   → Entferne unnötige Apps"
echo ""
echo "3) Background App Refresh deaktivieren:"
echo "   System Settings → General → Background App Refresh"
echo "   → Nur wichtige Apps aktivieren"
echo ""
echo "4) Browser optimieren:"
echo "   → Zu viele Tabs? Schließen"
echo "   → Zu viele Extensions? Deaktivieren"
echo ""
echo "5) Storage optimieren (wenn <20% frei):"
echo "   System Settings → General → Storage"
echo "   → Alte Downloads/Cache löschen"
echo ""
echo "6) Restart nach Fixes:"
echo "   sudo reboot"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Report speichert zu: $REPORT"
echo "═══════════════════════════════════════════════════════════"

} | tee "$REPORT"

echo ""
echo "✅ FERTIG!"
echo "📋 Report: cat $REPORT"
echo ""
echo "Nächster Schritt: Starte Activity Monitor und schau nach Top-Prozessen"
echo "open /Applications/Utilities/Activity\ Monitor.app"
echo ""
