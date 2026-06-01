# Apex Ecosystem — Sync Briefing 29.05.2026

_Stand: 29.05.2026 | Vorbereitet für: Claude Code + Hermes_

---

## Executive Summary

ApexCore V1 ist live. Alle Kerndienste laufen auf dem VPS (76.13.138.73, KVM8). Der Dispatcher ist aktiv. n8n ist konfiguriert. Caddy wurde durch nginx ersetzt. Paperclip Phase 1 gestartet.

---

## Stack Status

| Service | Status | Port | Domain |
|---|---|---|---|
| hermes-agent (LiteLLM) | ✅ Running | 127.0.0.1:4000 | intern |
| open-webui | ✅ Running | 127.0.0.1:3000 | ai.apexcore.group |
| hermes-webui | ✅ Running | 127.0.0.1:3001 | hermes.apexcore.group |
| n8n | ✅ Running | 127.0.0.1:5678 | n8n.apexcore.group |
| ollama | ✅ Running | 127.0.0.1:11434 | intern |
| dispatcher | ✅ Running | 7071 | intern |
| cmd-api | ✅ Running | 7070 | intern |
| openclaw | ⏸ Profile ops | 127.0.0.1:8000 | ops.apexcore.group |
| nginx (host) | ✅ Running | 80/443 | alle Domains |
| caddy | ⛔ Deaktiviert | — | (nginx übernimmt) |

---

## Was seit letztem Briefing gebaut wurde

### Hermes Dispatcher (cmd-api/hermes_dispatcher.py)
- Vollständiger Intent-Router auf Port 7071
- 6 Intent-Klassen: RESEARCH, SYSTEM, PRODUCT, CONTENT, CLIENT, ADMIN
- Bearer Token Auth via `DISPATCHER_TOKEN`
- JSON Structured Logging (ein Eintrag pro Zeile)
- Endpoints: `GET /health`, `GET /routes`, `POST /dispatch`
- systemd Unit: `cmd-api/apexcore-dispatcher.service`

### n8n Workflows (n8n-workflows/)
- **04-daily-brief.json** — Cron Mo-Fr 07:00 → Hermes → Audit-Log
- **05-completion-notify.json** — POST /webhook/log → Telegram + Notion
- **06-openwebui-hook.json** — POST /webhook/dispatch → Dispatcher → Antwort

### Infrastruktur
- Caddy profile-gated (kein Port-Konflikt mehr mit nginx)
- `infra-compose/nginx-vhost.conf` — vollständige nginx-Konfiguration
- n8n_data Volume: `external: true` (kein Compose-Warning mehr)
- hermes-webui healthcheck: python3-Fallback ergänzt
- GitHub Actions: deploys nginx-vhost statt Caddyfile

---

## Offene Punkte

### Schritt 3 — Dispatcher Hook finalisieren

```bash
# 1. DISPATCHER_TOKEN in .env.dispatcher prüfen
grep DISPATCHER_TOKEN /srv/apexcore/cmd-api/.env.dispatcher

# 2. Token auch in automation-stack/.env setzen (gleicher Wert)
echo "DISPATCHER_TOKEN=<token>" >> /srv/apexcore/automation-stack/.env

# 3. n8n Stack neu starten (damit DISPATCHER_TOKEN greift)
cd /srv/apexcore
docker compose -f automation-stack/docker-compose.yml down
docker compose -f automation-stack/docker-compose.yml up -d

# 4. Workflow 06 in n8n UI importieren
# n8n UI → Workflows → Import from File
# Datei: /srv/apexcore/n8n-workflows/06-openwebui-hook.json
# → Toggle "Active" einschalten
```

### Schritt 4 — Smoke Tests

```bash
# Dispatcher health
curl -s http://localhost:7071/health

# Dispatcher dispatch
curl -s -X POST http://localhost:7071/dispatch \
  -H "Authorization: Bearer $DISPATCHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task": "Research Bitcoin wallets 2026"}' | python3 -m json.tool

# n8n webhook
curl -s -X POST https://n8n.apexcore.group/webhook/dispatch \
  -H "Content-Type: application/json" \
  -d '{"message": "system status check"}' | python3 -m json.tool
```

Oder via Script:
```bash
/srv/apexcore/scripts/smoke-test.sh
```

---

## ENV-Checkliste (vor Go-Live)

### ai-stack/.env
- [ ] `OPENROUTER_API_KEY` gesetzt
- [ ] `LITELLM_MASTER_KEY` gesetzt

### automation-stack/.env
- [ ] `N8N_BASIC_AUTH_PASSWORD` gesetzt
- [ ] `N8N_ENCRYPTION_KEY` gesetzt (Original-Wert beibehalten!)
- [ ] `LITELLM_MASTER_KEY` gesetzt (gleich wie ai-stack)
- [ ] `DISPATCHER_TOKEN` gesetzt (gleich wie .env.dispatcher)

### cmd-api/.env.dispatcher
- [ ] `DISPATCHER_TOKEN` gesetzt (`openssl rand -hex 24`)
- [ ] `LITELLM_MASTER_KEY` gesetzt
- [ ] `CMD_TOKEN` gesetzt

---

## Architektur-Kurzüberblick

```
Browser / Open WebUI
  → POST https://n8n.apexcore.group/webhook/dispatch
  → n8n (Workflow 06)
  → http://host.docker.internal:7071/dispatch   (Bearer: DISPATCHER_TOKEN)
  → Hermes Dispatcher (Port 7071, VPS-Host)
      ├─ SYSTEM  → cmd-api:7070/status
      ├─ ADMIN   → n8n:5678/webhook/task
      ├─ CLIENT  → hermes-agent:4000 + openclaw:8000
      └─ *       → hermes-agent:4000 (LiteLLM → OpenRouter)
  → Antwort zurück an Open WebUI
```

---

## Nächste Schritte

1. **Dispatcher Hook aktivieren** — Workflow 06 in n8n importieren + Toggle
2. **Smoke-Test** — `scripts/smoke-test.sh`
3. **Paperclip Phase 2** — Echtes Image deployen wenn verfügbar
4. **OpenClaw** — `--profile ops` aktivieren wenn Image verfügbar
5. **Notion-Integration** — n8n Credentials eintragen, Workflows 04+05 aktivieren
