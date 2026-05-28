# Runbook: ApexCore Orchestration V1

_Operativer Leitfaden | VPS: 76.13.138.73 | Root: /srv/apexcore_

---

## Erstmaliges Setup (einmalig)

```bash
# 1. Repo auf VPS clonen (oder sync via deploy)
git clone https://github.com/AIA2025/apexcore /srv/apexcore

# 2. .env-Dateien anlegen (NICHT commiten!)
cp /srv/apexcore/infra-compose/.env.example      /srv/apexcore/infra-compose/.env
cp /srv/apexcore/ai-stack/.env.example           /srv/apexcore/ai-stack/.env
cp /srv/apexcore/automation-stack/.env.example   /srv/apexcore/automation-stack/.env

# 3. Werte in .env-Dateien eintragen
nano /srv/apexcore/ai-stack/.env           # OPENROUTER_API_KEY, LITELLM_MASTER_KEY
nano /srv/apexcore/automation-stack/.env  # N8N_BASIC_AUTH_PASSWORD, N8N_ENCRYPTION_KEY
nano /srv/apexcore/infra-compose/.env      # CADDY_EMAIL

# 4. Scripts ausführbar machen
chmod +x /srv/apexcore/scripts/*.sh
```

---

## Stack starten

```bash
# Alles auf einmal (empfohlen)
/srv/apexcore/scripts/stack-start.sh

# Oder manuell in Reihenfolge:
cd /srv/apexcore
docker compose -f ai-stack/docker-compose.yml up -d
docker compose -f automation-stack/docker-compose.yml up -d
docker compose -f infra-compose/docker-compose.yml up -d
```

**Reihenfolge wichtig:** ai-stack und automation-stack müssen vor Caddy laufen,
damit die Docker-Netze `ai_net` und `automation_net` existieren.

---

## Stack stoppen

```bash
/srv/apexcore/scripts/stack-stop.sh

# Oder manuell (umgekehrte Reihenfolge):
cd /srv/apexcore
docker compose -f infra-compose/docker-compose.yml down
docker compose -f automation-stack/docker-compose.yml down
docker compose -f ai-stack/docker-compose.yml down
```

---

## Health Check

```bash
/srv/apexcore/scripts/healthcheck.sh
```

Schnell-Check per Hand:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | sort
```

---

## Diagnose-Befehle

```bash
# Logs eines Services
docker logs open-webui --tail 50 -f
docker logs hermes-agent --tail 50 -f
docker logs n8n --tail 50 -f
docker logs caddy --tail 50 -f

# Hermes Agent API erreichbar?
curl http://localhost:4000/health

# Open WebUI erreichbar (intern)?
curl http://localhost:3000/health

# n8n läuft?
curl http://localhost:5678/healthz

# Caddy Config valide?
docker exec caddy caddy validate --config /etc/caddy/Caddyfile

# Caddy Logs
docker exec caddy caddy logs

# Netzwerk-Memberships prüfen
docker inspect caddy | grep -A 10 '"Networks"'
docker network inspect ai_net
docker network inspect automation_net
```

---

## Caddy neu laden (nach Caddyfile-Änderung)

```bash
docker exec caddy caddy validate --config /etc/caddy/Caddyfile
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

---

## Open WebUI → Hermes Verbindung prüfen

```bash
# Hermes API direkt testen
curl -s http://localhost:4000/v1/models \
  -H "Authorization: Bearer $(grep LITELLM_MASTER_KEY /srv/apexcore/ai-stack/.env | cut -d= -f2)"

# Sollte eine Modellliste zurückgeben
```

Falls keine Verbindung: prüfe ob `open-webui` und `hermes-agent` im selben Netz sind:
```bash
docker network inspect ai_net | grep -E '"Name"|"IPv4"'
```

---

## n8n Verbindung prüfen

```bash
# n8n Web UI
curl -sk https://n8n.apexcore.group/ | grep -i "n8n"

# Webhook-Test (ersetzt WEBHOOK_ID mit echtem Wert aus n8n)
curl -X POST https://n8n.apexcore.group/webhook/test -d '{"test": true}'
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
# Caddy-Config zurücksetzen (Backups unter /opt/openclaw/reverse-proxy/)
ls /opt/openclaw/reverse-proxy/Caddyfile.bak.*
cp /opt/openclaw/reverse-proxy/Caddyfile.bak.YYYYMMDD_HHMMSS \
   /opt/openclaw/reverse-proxy/Caddyfile
docker exec caddy caddy reload --config /etc/caddy/Caddyfile

# Service auf vorherige Version zurücksetzen
docker compose -f ai-stack/docker-compose.yml pull
docker compose -f ai-stack/docker-compose.yml up -d
```

---

## Volumes erhalten bei Container-Update

Volumes werden durch `docker compose down` NICHT gelöscht. Sicher:
```bash
docker compose -f ai-stack/docker-compose.yml down    # Volumes bleiben
docker compose -f ai-stack/docker-compose.yml pull    # Neue Images ziehen
docker compose -f ai-stack/docker-compose.yml up -d   # Neu starten
```

Volumes explizit löschen (DESTRUKTIV, Datenverlust!):
```bash
docker compose -f ai-stack/docker-compose.yml down -v   # ← nur wenn gewollt
```
