# Runbook: ApexCore Orchestration V1

_Operativer Leitfaden | VPS: 76.13.138.73 | Root: /srv/apexcore_

---

## Erstmaliges Setup (einmalig auf dem VPS)

```bash
# 1. Sicherstellen dass /srv/apexcore/ mit Repo-Inhalt befüllt ist
#    (passiert automatisch via deploy.yml nach dem ersten Push)
ls /srv/apexcore/

# 2. .env-Dateien anlegen (NICHT ins Git commiten — .gitignore schützt sie)
cp /srv/apexcore/ai-stack/.env.example         /srv/apexcore/ai-stack/.env
cp /srv/apexcore/automation-stack/.env.example /srv/apexcore/automation-stack/.env
cp /srv/apexcore/infra-compose/.env.example    /srv/apexcore/infra-compose/.env

# 3. Secrets eintragen
nano /srv/apexcore/ai-stack/.env
#   → OPENROUTER_API_KEY=sk-or-v1-...
#   → LITELLM_MASTER_KEY=sk-hermes-... (generate: openssl rand -hex 24)

nano /srv/apexcore/automation-stack/.env
#   → N8N_BASIC_AUTH_PASSWORD=strong-password
#   → N8N_ENCRYPTION_KEY=... (generate: openssl rand -hex 32)
#   → LITELLM_MASTER_KEY=sk-hermes-... (gleicher Wert wie in ai-stack/.env!)

nano /srv/apexcore/infra-compose/.env
#   → CADDY_EMAIL=admin@apexcore.group

# 4. Scripts ausführbar machen
chmod +x /srv/apexcore/scripts/*.sh
```

---

## Stacks starten

```bash
# Empfohlen: alles auf einmal in korrekter Reihenfolge
/srv/apexcore/scripts/stack-start.sh

# Alternativ manuell (Reihenfolge beachten!):
cd /srv/apexcore
docker compose -f ai-stack/docker-compose.yml         up -d --remove-orphans
docker compose -f automation-stack/docker-compose.yml up -d --remove-orphans
docker compose -f infra-compose/docker-compose.yml    up -d --remove-orphans
```

**Reihenfolge ist kritisch:**
- ai-stack muss zuerst starten → erstellt `ai_net`
- automation-stack muss nach ai-stack starten → joined `ai_net` als external
- infra-compose (Caddy) muss zuletzt starten → joined beide Netze als external

---

## Stacks stoppen

```bash
/srv/apexcore/scripts/stack-stop.sh

# Volumes BEHALTEN (Standard) — Daten bleiben erhalten
# Volumes LÖSCHEN (DESTRUKTIV — alle Daten weg!):
/srv/apexcore/scripts/stack-stop.sh --volumes
```

---

## Health Check

```bash
/srv/apexcore/scripts/healthcheck.sh
```

Schnell-Check:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | sort
```

---

## Diagnose-Befehle

```bash
# Service-Logs
docker logs open-webui   --tail 50 -f
docker logs hermes-agent --tail 50 -f
docker logs n8n          --tail 50 -f
docker logs caddy        --tail 50 -f

# Hermes API erreichbar?
curl -s http://localhost:4000/health
curl -s http://localhost:4000/v1/models \
  -H "Authorization: Bearer $(grep LITELLM_MASTER_KEY /srv/apexcore/ai-stack/.env | cut -d= -f2)"

# n8n erreichbar?
curl -s http://localhost:5678/healthz

# Open WebUI erreichbar (intern)?
curl -s http://localhost:3000/health

# Netzwerke prüfen
docker network inspect ai_net | grep -E '"Name"|"IPv4'
docker network inspect automation_net | grep -E '"Name"|"IPv4'

# Caddy Config validieren
docker exec caddy caddy validate --config /etc/caddy/Caddyfile

# Netz-Membership von n8n prüfen (muss in ai_net UND automation_net sein)
docker inspect n8n | python3 -c "import sys,json; d=json.load(sys.stdin); print(list(d[0]['NetworkSettings']['Networks'].keys()))"
```

---

## Caddy neu laden

```bash
# Validieren dann reload (kein Downtime)
docker exec caddy caddy validate --config /etc/caddy/Caddyfile && \
docker exec caddy caddy reload   --config /etc/caddy/Caddyfile
```

---

## Open WebUI → Hermes Verbindung prüfen

```bash
HERMES_KEY=$(grep LITELLM_MASTER_KEY /srv/apexcore/ai-stack/.env | cut -d= -f2)

# Modelle abrufen
curl -s http://localhost:4000/v1/models -H "Authorization: Bearer $HERMES_KEY" | python3 -m json.tool

# Test-Chat
curl -s http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $HERMES_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"hermes-default","messages":[{"role":"user","content":"ping"}]}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

---

## n8n → Hermes Verbindung prüfen

n8n greift über den internen Container-Namen auf Hermes zu (ai_net-Mitgliedschaft):

```bash
# Aus dem n8n-Container heraus Hermes erreichen
docker exec n8n wget -qO- http://hermes-agent:4000/health
```

Falls der Befehl scheitert: n8n ist nicht in ai_net — Netzwerk-Mitgliedschaft prüfen:
```bash
docker inspect n8n | python3 -c "import sys,json; print(list(json.load(sys.stdin)[0]['NetworkSettings']['Networks'].keys()))"
# Erwartetes Ergebnis: ['automation_net', 'ai_net'] (beide)
```

---

## OpenClaw aktivieren (wenn Image vorhanden)

```bash
# 1. Image in .env setzen
echo "OPENCLAW_IMAGE=ghcr.io/aia2025/openclaw:latest" >> /srv/apexcore/ai-stack/.env

# 2. Mit ops-Profil starten
cd /srv/apexcore
docker compose -f ai-stack/docker-compose.yml --profile ops up -d

# 3. Erreichbar?
curl http://localhost:8000/
```

---

## Einzelnen Service neu starten

```bash
docker restart open-webui
docker restart hermes-agent
docker restart n8n
docker restart caddy
```

---

## Rollback

```bash
# Caddy-Config zurücksetzen (Backups in /srv/apexcore/backups/)
ls /srv/apexcore/backups/Caddyfile.bak.*
cp /srv/apexcore/backups/Caddyfile.bak.YYYYMMDD_HHMMSS \
   /srv/apexcore/infra-compose/Caddyfile
docker exec caddy caddy reload --config /etc/caddy/Caddyfile

# Service auf vorherige Image-Version zurücksetzen (Volumes bleiben)
docker compose -f ai-stack/docker-compose.yml down
# → Image-Tag in docker-compose.yml auf alte Version setzen
docker compose -f ai-stack/docker-compose.yml up -d
```

---

## Volumes erhalten bei Image-Update

`docker compose down` löscht KEINE named volumes. Sicher aktualisieren:

```bash
docker compose -f ai-stack/docker-compose.yml down          # Container weg, Volumes bleiben
docker compose -f ai-stack/docker-compose.yml pull          # Neue Images
docker compose -f ai-stack/docker-compose.yml up -d         # Neu starten
```

`docker compose down -v` hingegen löscht Volumes — nur mit Bedacht nutzen.
