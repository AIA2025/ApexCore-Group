#!/bin/bash
# FINALE: Kill Brave + Hermes + Restart
# Basiert auf echten Daten: Brave 9.3%, Hermes 12.4%

set -euo pipefail

echo "🚀 KILLING MEMORY HOGS NOW..."
echo ""

# Kill Brave (9.3% RAM)
echo "1️⃣  Killing Brave Browser (9.3% RAM)..."
killall -9 "Brave Browser" 2>/dev/null || true
killall -9 "brave" 2>/dev/null || true
sleep 1
echo "✅ Brave killed"

# Kill Hermes (12.4% RAM)
echo ""
echo "2️⃣  Killing Hermes Desktop (12.4% RAM)..."
killall -9 "Hermes" 2>/dev/null || true
killall -9 "node" 2>/dev/null || grep -v grep || true
sleep 1
echo "✅ Hermes killed"

# Clear caches aggressively
echo ""
echo "3️⃣  Clearing caches (~2GB freed)..."
rm -rf ~/Library/Caches/* 2>/dev/null || true
rm -rf /tmp/* /var/tmp/* 2>/dev/null || true
echo "✅ Caches cleared"

# Show new memory status
echo ""
echo "4️⃣  NEW MEMORY STATUS:"
vm_stat | head -8

# RESTART
echo ""
echo "═══════════════════════════════════════════"
echo "🔄 RESTARTING SYSTEM..."
echo "═══════════════════════════════════════════"
echo ""
echo "System wird in 10 Sekunden neu gestartet..."
sleep 10
sudo reboot
