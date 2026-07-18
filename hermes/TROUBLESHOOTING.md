# Hermes — Troubleshooting-Wissen (Session 2026-07-18)

> Gesammelte Erkenntnisse aus der Migration Hermes Desktop (iMac) → VPS und der
> anschließenden Login/Passwort-Verwirrung. Für zukünftige Sessions (Claude Code
> oder Hermes selbst) gedacht, damit dieselben Missverständnisse nicht erneut
> Zeit kosten.

## 1. Zwei völlig getrennte Systeme — nicht verwechseln

- **Hermes Desktop** — die App, die lokal auf dem Rechner des Nutzers läuft
  (iMac und/oder Linux-Laptop). Kann im **Local**- oder **Remote-Gateway**-Modus
  laufen.
- **Hermes Dashboard** — die Web-Oberfläche des VPS-Containers (`hermes-webui`),
  erreichbar unter `https://hermes.apexcore.group`. Läuft in Docker auf
  `76.13.138.73`, teilt sich mit dem Container `hermes` den Host-Mount
  `/root/.hermes` → `/opt/data`.

**Wichtige Erkenntnis:** Wenn Hermes Desktop im **Remote-Gateway**-Modus läuft
und "Remote gateway sign-in required" (OAuth-Session abgelaufen) zeigt, öffnet
"Sign out & sign in" ein Login-Formular, das **exakt dasselbe** `basic_auth` aus
der Dashboard-`config.yaml` prüft (Username + Passwort). Es ist **derselbe
Login** wie der Browser-Zugang zu `hermes.apexcore.group/login` — keine
separate OAuth-Identität. Das hat in dieser Session zu viel Verwirrung geführt,
weil "Passwort für Hermes" zunächst als reine Dashboard-Frage missverstanden
wurde.

## 2. Dashboard-Login: `basic_auth`-Struktur in `/root/.hermes/config.yaml`

```yaml
dashboard:
  basic_auth:
    username: maki
    password_hash: scrypt$...      # ← DAS wird tatsächlich geprüft
    password: null                  # ← Klartext-Legacy-Feld, ungenutzt (bereinigt)
    secret: ...
    session_ttl_seconds: 604800
```

`password_hash` (scrypt) ist das aktive Feld. Ein zusätzliches Klartext-Feld
`password` existierte parallel (alter Stand) und hat für Verwirrung gesorgt,
weil es einen anderen Wert enthielt — wurde entfernt (`null`).

**Neues Passwort setzen (Muster, das funktioniert hat):**

```bash
ssh root@76.13.138.73 bash -s <<'REMOTE'
set -e
cp /root/.hermes/config.yaml /root/.hermes/config.yaml.bak-$(date +%Y%m%d_%H%M%S)
HASH=$(docker exec hermes python -c "from plugins.dashboard_auth.basic import hash_password; print(hash_password('NEUES_PASSWORT'))")
python3 - "$HASH" <<'PY'
import re, sys
hash_val = sys.argv[1]
path = "/root/.hermes/config.yaml"
content = open(path).read()
content = re.sub(r'(password_hash:\s*).*', r'\g<1>"' + hash_val + '"', content, count=1)
open(path, "w").write(content)
PY
docker restart hermes hermes-webui
REMOTE
```

## 3. Lokaler Modell-Konfigurationsfehler (iMac/Laptop `~/.hermes/config.yaml`)

Fehler beim Start von `hermes`:
```
{"default": "nvidia/nemotron-3-ultra-550b-a55b:free", "provider": "openrouter"} is not a valid model ID
```
Ursache: Das `model:`-Feld enthielt das **komplette JSON-Objekt** statt nur
der Modell-ID. Fix: nur den reinen String eintragen, z. B.
```yaml
model: nvidia/nemotron-3-ultra-550b-a55b:free
```

## 4. Kontextfenster-Falle: nie `grep -rn` gegen die Hermes-Cache-Dateien

`~/.hermes/models_dev_cache.json`, `provider_models_cache.json` und
`ollama_cloud_models_cache.json` sind **eine einzige minifizierte JSON-Zeile**
pro Datei (mehrere MB). `grep -n` gibt bei einem Treffer die **komplette
Zeile** aus — das kann leicht mehrere MB / über eine Million Tokens Text
erzeugen und jedes Kontextfenster sprengen (ist in dieser Session passiert,
hat eine Compaction zerschossen).

**Richtig:**
```bash
grep -o '.\{0,80\}SUCHBEGRIFF.\{0,80\}' ~/.hermes/*.json
# oder, falls jq verfügbar:
jq -r '.. | objects | select(.id? == "SUCHBEGRIFF")' ~/.hermes/models_dev_cache.json
```

## 5. Migrations-Stand (abgeschlossen)

- iMac-`~/.hermes` (Skills, Config, Memories, Sessions, Cron) wurde per
  `hermes/hermes-vps-migrate.sh` + `hermes/hermes-vps-migrate-finish.sh` in
  `/root/.hermes` auf dem VPS gemerged (rsync, nichts gelöscht, Backups unter
  `/root/backups/`).
- Betroffene Container: `hermes-webui` und `hermes` (beide mounten
  `/root/.hermes` → `/opt/data`). `hermes-agent` ist der separate LiteLLM-Proxy
  (aus PR #8/#11) und **nicht** Teil dieses Datenpfads.
- Transfer nutzt `rsync --partial` + SSH-Keepalive (siehe
  `hermes-vps-migrate-finish.sh`), damit Abbrüche bei langsamem Upload
  fortsetzbar sind statt bei 0 % neu zu beginnen.

## 6. Terminologie: der Nutzer sagt "Hermes Desktop", nicht "Dashboard"

Der Nutzer benutzt **ausschließlich** die Bezeichnung "Hermes Desktop" für die
App, egal ob sie Local oder Remote läuft. "Dashboard" ist nur der interne
Name des Server-Prozesses (`hermes-webui`), auf den Hermes Desktop im
Remote-Modus zugreift — kein separates Produkt aus Nutzersicht. In
Antworten und Diagnosen **immer "Hermes Desktop" sagen**, "Dashboard" nur
verwenden, wenn technisch explizit der VPS-Serverprozess gemeint ist, und
das dann auch so einordnen ("das Server-Gegenstück, mit dem Hermes Desktop
im Remote-Modus spricht").

## 7. 502 Bad Gateway — Ursache & YAML-Falle beim Modellwechsel

**Vorfall:** Hermes Desktop (Remote) konnte sich nicht mehr verbinden,
`https://hermes.apexcore.group/login` lieferte 502.

**Root Cause #1 (Auslöser):** `hermes-webui` nutzte das Free-Tier-Modell
`nvidia/nemotron-3-ultra-550b-a55b:free` über OpenRouter. Dessen Rate-Limit
(32 Requests) wurde weit überschritten (`ResourceExhausted ... 365/32`),
nach 3 gescheiterten Retries stoppen alle s6-Services intern und der
Container beendet sich (`Exited (0)`/`(1)`). Der Reverse-Proxy davor ist
**nginx** (nicht Caddy, wie `docs/RUNBOOKORCHESTRATIONV1.md` behauptet —
Doku ist an der Stelle veraltet) und antwortet dann mit 502, weil kein
Backend mehr lauscht.

**Root Cause #2 (durch den ersten Fix-Versuch selbst verursacht):** In
`/root/.hermes/config.yaml` ist `model:` **kein einzeiliger String**,
sondern ein Mapping:
```yaml
model:
  default: nvidia/nemotron-3-ultra-550b-a55b:free
  provider: openrouter
```
Ein `sed -i 's|^model:.*|model: NEUES_MODELL|'` ersetzt nur Zeile 1 und
lässt die alte `default:`/`provider:`-Zeile darunter stehen → ungültiges
YAML ("mapping values are not allowed in this context") → Config wird
komplett verworfen → Fallback-Config hat keinen Auth-Provider →
`hermes-webui` verweigert den Start ganz (Exit Code 1). **Lehre: Modell-
Feld in dieser config.yaml nie mit zeilenbasiertem `sed` anfassen,
sondern gezielt nur die `default:`-Unterzeile ersetzen (Zeile bekannt
über `sed -n '1,4p'` vorher prüfen) oder mit `python3 -c "import yaml"`
laden/ändern/schreiben, und immer `yaml.safe_load()` **vor** dem
Container-Neustart validieren.**

**Fix, der funktioniert hat:**
```bash
ssh root@76.13.138.73 bash -s <<'REMOTE'
set -e
cp /root/.hermes/config.yaml /root/.hermes/config.yaml.broken-$(date +%Y%m%d_%H%M%S)
LAST_BACKUP=$(ls -t /root/.hermes/config.yaml.bak-2* | head -1)
cp "$LAST_BACKUP" /root/.hermes/config.yaml
sed -i '2s|.*|  default: anthropic/claude-haiku-4.5|' /root/.hermes/config.yaml
python3 -c "import yaml; yaml.safe_load(open('/root/.hermes/config.yaml')); print('YAML OK')"
docker start hermes-webui
docker restart hermes
REMOTE
```
Aktuelles Dashboard-Modell: `anthropic/claude-haiku-4.5` (bezahlt, kein
Free-Tier-Rate-Limit-Absturzrisiko mehr wie bei Nemotron-free).
