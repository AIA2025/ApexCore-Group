#!/bin/bash
# macOS iMac Performance Diagnostics & Fixes
# Diagnose warum das System langsam ist

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; }
h()    { echo -e "\n${BOLD}━━━ $1 ━━━${NC}"; }

h "macOS Performance Diagnostics"

# ═══════════════════════════════════════════════════════════════
# 1. CPU & Memory
# ═══════════════════════════════════════════════════════════════
h "1) CPU & Memory Auslastung"
echo ""
top -l 1 | head -15
echo ""

# ═══════════════════════════════════════════════════════════════
# 2. Top Prozesse (CPU)
# ═══════════════════════════════════════════════════════════════
h "2) Top 10 Prozesse (nach CPU)"
echo ""
ps aux | sort -k 3 -rn | head -11 | awk '{printf "%-20s %5s%% %s\n", $1, $3, $11}'
echo ""

# ═══════════════════════════════════════════════════════════════
# 3. Top Prozesse (Memory)
# ═══════════════════════════════════════════════════════════════
h "3) Top 10 Prozesse (nach RAM)"
echo ""
ps aux | sort -k 4 -rn | head -11 | awk '{printf "%-20s %5s%% %s\n", $1, $4, $11}'
echo ""

# ═══════════════════════════════════════════════════════════════
# 4. Disk-Auslastung
# ═══════════════════════════════════════════════════════════════
h "4) Festplatte"
echo ""
df -h | grep -E "Filesystem|/dev/disk"
echo ""

# ═══════════════════════════════════════════════════════════════
# 5. RAM Details
# ═══════════════════════════════════════════════════════════════
h "5) RAM Memory Details"
echo ""
vm_stat | head -15
echo ""

# ═══════════════════════════════════════════════════════════════
# 6. Aktive Netzwerk Verbindungen
# ═══════════════════════════════════════════════════════════════
h "6) Netzwerk"
ESTABLISHED=$(netstat -an 2>/dev/null | grep ESTABLISHED | wc -l)
LISTENING=$(netstat -an 2>/dev/null | grep LISTEN | wc -l)
echo "  Established connections: $ESTABLISHED"
echo "  Listening ports: $LISTENING"
echo ""

# ═══════════════════════════════════════════════════════════════
# 7. Disk I/O
# ═══════════════════════════════════════════════════════════════
h "7) Disk Activity (letzte 10 Sekunden)"
echo ""
iostat -w 2 2 | tail -10 || echo "  (iostat nicht verfügbar)"
echo ""

# ═══════════════════════════════════════════════════════════════
# 8. Launch Services / Startups
# ═══════════════════════════════════════════════════════════════
h "8) Startup Items & Services"
echo ""
echo "  Login Items (System Preferences):"
if [ -f "$HOME/Library/Preferences/com.apple.loginitems.plist" ]; then
  echo "    Found: com.apple.loginitems.plist"
else
  echo "    (check manually in System Settings → General → Login Items)"
fi
echo ""

# ═══════════════════════════════════════════════════════════════
# 9. Swap Usage
# ═══════════════════════════════════════════════════════════════
h "9) Swap / Speicherdruck"
echo ""
if [ -x "$(command -v sysctl)" ]; then
  sysctl -n vm.swapusage 2>/dev/null || echo "  (not available)"
else
  echo "  (sysctl nicht verfügbar)"
fi
echo ""

# ═══════════════════════════════════════════════════════════════
# 10. Thermals (wenn verfügbar)
# ═══════════════════════════════════════════════════════════════
h "10) System Thermals & Power"
echo ""
if [ -x "$(command -v powermetrics)" ]; then
  echo "  Running: sudo powermetrics --n 1"
  sudo powermetrics --n 1 2>/dev/null | grep -iE "cpu|gpu|thermal|temp" | head -10
else
  echo "  (powermetrics nicht verfügbar - CPU Temp via System Report)"
fi
echo ""

# ═══════════════════════════════════════════════════════════════
# 11. Background App Refresh
# ═══════════════════════════════════════════════════════════════
h "11) Background App Settings"
echo ""
echo "  Check in: System Settings → General → Background App Refresh"
echo "  Disable apps that don't need background activity"
echo ""

# ═══════════════════════════════════════════════════════════════
# SUMMARY & RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════
h "SUMMARY & FIXES"
echo ""
echo "🔍 Häufige Ursachen für Slowdown:"
echo "  1. Zu viele Prozesse aktiv (Task Manager prüfen)"
echo "  2. RAM voll → Swap wird genutzt (sehr langsam)"
echo "  3. Festplatte fast voll"
echo "  4. Background Apps (Sync, iCloud, Antivirus)"
echo "  5. Browser Tabs & Extensions"
echo "  6. Activity Monitor zeigt die Verursacher"
echo ""
echo "✅ Schnelle Fixes:"
echo "  1. Activity Monitor öffnen:"
echo "     open /Applications/Utilities/Activity\ Monitor.app"
echo ""
echo "  2. Neustart:"
echo "     sudo reboot"
echo ""
echo "  3. Cache löschen:"
echo "     rm -rf ~/Library/Caches/*"
echo ""
echo "  4. Temporäre Dateien:"
echo "     rm -rf /tmp/* /var/tmp/*"
echo ""
echo "  5. Disk Space freigeben (bei <10% frei):"
echo "     df -h  (check Prozentual)"
echo ""

h "DONE"
echo ""
echo "📋 Kopiere diese Ausgabe und sende sie an Claude!"
echo ""
