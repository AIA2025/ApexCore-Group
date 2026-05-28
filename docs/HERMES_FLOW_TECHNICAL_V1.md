# Hermes Flow — Technische Implementierung V1

_Open WebUI → Hermes → Worker: vollständige technische Spezifikation_
_Stand: 2026-05-28_

---

## Architektur-Überblick

```
Open WebUI / n8n Webhook / Extern
        │
        │ POST /dispatch   (Bearer: DISPATCHER_TOKEN)
        ▼
┌──────────────────────────┐
│  Hermes Dispatcher       │  Port 7071 — cmd-api/hermes_dispatcher.py
│  Intent Classification   │  Klassifiziert: RESEARCH / SYSTEM / PRODUCT
│  + Routing               │                CONTENT / CLIENT / ADMIN
└────────────┬─────────────┘
             │
     ┌───────┼──────────────────────────┐
     │       │                          │
     ▼       ▼                          ▼
hermes-agent:4000   cmd-api:7070    n8n Webhook
(LiteLLM/OpenRouter) (/status)    (webhook/task)
     │                                  │
     ▼                                  ▼
OpenRouter API                     Notion API
(Claude, Kimi, auto)               (via n8n)
     │
     ▼
openclaw:8000
(wenn intent=CLIENT + options.notify=true)
```

---

## Pfad-Mapping

| Referenz im Briefing | Tatsächlicher Pfad |
|---|---|
| `/data/apex-core-central/` | `/srv/apexcore/` (VPS) |
| `/data/apex-core-central/scripts/` | `/srv/apexcore/cmd-api/` |
| `hermes_dispatcher.py` | `/srv/apexcore/cmd-api/hermes_dispatcher.py` |

Das Briefing verwendet `/data/apex-core-central/` als abstraktes Referenzpfad-Konzept. Die tatsächliche Deployment-Struktur auf dem VPS ist `/srv/apexcore/` — wie in `RUNBOOK_ORCHESTRATION_V1.md` und `deploy.yml` definiert.

---

## Hermes Dispatcher — Technische Spezifikation

**Datei:** `cmd-api/hermes_dispatcher.py`
**Port:** `7071` (intern, ai_net)
**Auth:** Bearer Token via `DISPATCHER_TOKEN` env var
**Deps:** Python 3 stdlib only — kein pip, kein virtualenv

### Endpoints

| Methode | Pfad | Auth | Beschreibung |
|---|---|---|---|
| `GET` | `/health` | nein | Liveness check |
| `GET` | `/routes` | ja | Aktuelle Routing-Tabelle anzeigen |
| `POST` | `/dispatch` | ja | Task einreichen, Intent klassifizieren, routen |

### Request-Format `/dispatch`

```json
{
  "task": "Research the top 3 AI newsletter platforms",
  "options": {
    "notify": false,
    "channel": "telegram"
  }
}
```

### Response-Format

```json
{
  "task_id": "a3f9c1b2",
  "status": "DONE",
  "intent": "RESEARCH",
  "worker": "hermes-agent",
  "result": {
    "response": "...",
    "model": "hermes-default"
  },
  "started_at": "2026-05-28T10:00:00+00:00",
  "completed_at": "2026-05-28T10:00:04+00:00"
}
```

### Status-Schema

| Status | Bedeutung |
|---|---|
| `DONE` | Worker hat geantwortet, kein Fehler |
| `BLOCKED` | Worker hat Fehler zurückgegeben (z.B. Hermes nicht erreichbar) |

---

## Intent-Routing-Tabelle

| Intent | Trigger-Wörter (Beispiele) | Worker | Modell |
|---|---|---|---|
| `RESEARCH` | research, analyze, find, explain, what is, who is | hermes-agent | kimi (langer Kontext) |
| `SYSTEM` | status, health, check, running, down, docker | cmd-api `/status` | — |
| `PRODUCT` | launch, publish, product, release, listing | hermes-agent + n8n log | hermes-default |
| `CONTENT` | write, draft, content, caption, copy | hermes-agent | hermes-default |
| `CLIENT` | client, message, send, notify, telegram, whatsapp | hermes-agent + openclaw | hermes-default |
| `ADMIN` | workflow, automation, sync, cron, n8n | n8n webhook/task | — |

**Default:** Kein Treffer → `RESEARCH` (produziert immer eine brauchbare LLM-Antwort).

---

## Beispiel-Abläufe

### 1. `Research [Topic]`

```
Input:  POST /dispatch {"task": "Research the top AI newsletter tools in 2026"}
Intent: RESEARCH
Worker: hermes-agent:4000/v1/chat/completions  (model: kimi)
Output: {
  "status": "DONE",
  "intent": "RESEARCH",
  "result": {"response": "Beehiiv, Substack, Kit (ConvertKit)..."}
}
```

### 2. `System Status`

```
Input:  POST /dispatch {"task": "System status check"}
Intent: SYSTEM
Worker: cmd-api:7070/status
Output: {
  "status": "DONE",
  "intent": "SYSTEM",
  "result": {"response": "**System Status**\n- hermes-agent: Up 2 hours\n- n8n: Up 2 hours\n..."}
}
```

### 3. `Launch Product [Name]`

```
Input:  POST /dispatch {"task": "Launch product ApexOS Starter Pack"}
Intent: PRODUCT
Worker: hermes-agent:4000  (primary) + n8n webhook/log (audit)
Output: {
  "status": "DONE",
  "intent": "PRODUCT",
  "result": {"response": "Launch plan für ApexOS Starter Pack: ..."}
}
Log:    n8n webhook/log empfängt task_id + result für Notion-Audit
```

---

## ENV-Keys — vollständige Liste

Alle Keys, die vor dem ersten Live-Test gesetzt sein müssen:

### ai-stack/.env

| Key | Zweck | Pflicht |
|---|---|---|
| `OPENROUTER_API_KEY` | Zugang zu Claude, Kimi, GPT-4o via OpenRouter | ✅ |
| `LITELLM_MASTER_KEY` | Auth-Token für Hermes Agent API | ✅ |
| `OPENCLAW_IMAGE` | Docker Image für OpenClaw (nur wenn ops-Profil aktiv) | ⚠️ ops |

### automation-stack/.env

| Key | Zweck | Pflicht |
|---|---|---|
| `N8N_BASIC_AUTH_PASSWORD` | Login-Schutz für n8n Web-UI | ✅ |
| `N8N_ENCRYPTION_KEY` | Verschlüsselung der Credentials in n8n | ✅ |
| `LITELLM_MASTER_KEY` | n8n → Hermes API Auth (gleicher Wert wie ai-stack!) | ✅ |

### infra-compose/.env

| Key | Zweck | Pflicht |
|---|---|---|
| `CADDY_EMAIL` | Let's Encrypt TLS-Zertifikat-Anfragen | ✅ |

### cmd-api / dispatcher (Umgebungsvariablen beim Start)

| Key | Zweck | Default |
|---|---|---|
| `DISPATCHER_TOKEN` | Auth-Token für /dispatch Endpoint | — (gesetzt = aktiviert) |
| `DISPATCHER_PORT` | Port des Dispatcher-Servers | `7071` |
| `HERMES_API_URL` | URL zu Hermes LiteLLM | `http://hermes-agent:4000/v1/chat/completions` |
| `LITELLM_MASTER_KEY` | Auth für Hermes API | — |
| `N8N_TASK_WEBHOOK` | n8n Webhook für neue Tasks | `https://n8n.apexcore.group/webhook/task` |
| `N8N_LOG_WEBHOOK` | n8n Webhook für Audit-Log | `https://n8n.apexcore.group/webhook/log` |
| `OPENCLAW_API_URL` | OpenClaw Messaging URL | `http://openclaw:8000/send` |
| `CMD_API_URL` | cmd-api /status für SYSTEM Intent | `http://localhost:7070/status` |
| `CMD_TOKEN` | Auth-Token für cmd-api | — |

---

## Dependency-Checkliste (vor Go-Live)

### Zwingend vor erstem `POST /dispatch`

- [ ] `hermes-agent` läuft: `curl http://localhost:4000/health`
- [ ] `OPENROUTER_API_KEY` gesetzt: `curl http://localhost:4000/v1/models -H "Authorization: Bearer $LITELLM_MASTER_KEY"`
- [ ] `LITELLM_MASTER_KEY` gesetzt und identisch in ai-stack/.env + automation-stack/.env
- [ ] `DISPATCHER_TOKEN` gesetzt (mindestens 24 Zeichen: `openssl rand -hex 24`)
- [ ] `cmd-api/server.py` läuft auf Port 7070 mit `CMD_TOKEN` gesetzt

### Zwingend für ADMIN-Intent (n8n-Routing)

- [ ] n8n läuft: `curl http://localhost:5678/healthz`
- [ ] n8n Webhook `/webhook/task` aktiv (Workflow aktiviert in n8n UI)
- [ ] n8n Webhook `/webhook/log` aktiv (Workflow aktiviert in n8n UI)
- [ ] `N8N_BASIC_AUTH_PASSWORD` gesetzt

### Für CLIENT-Intent (OpenClaw-Notification)

- [ ] OpenClaw-Image gesetzt in ai-stack/.env: `OPENCLAW_IMAGE=...`
- [ ] `docker compose -f ai-stack/docker-compose.yml --profile ops up -d` ausgeführt
- [ ] OpenClaw erreichbar: `curl http://localhost:8000/`

### Für PRODUCT/ADMIN-Intent (Notion-Audit-Log)

- [ ] Notion-Credentials in n8n eingetragen
- [ ] Notion-DB freigegeben für ApexCore n8n Integration
- [ ] `__NOTION_ID__` und `__NOTION_TASKS_DB_ID__` in Workflow-Templates gesetzt

---

## Dispatcher starten (VPS)

```bash
# Im Hintergrund starten
export DISPATCHER_TOKEN=$(openssl rand -hex 24)
export LITELLM_MASTER_KEY=$(grep LITELLM_MASTER_KEY /srv/apexcore/ai-stack/.env | cut -d= -f2)
export CMD_TOKEN=$(grep CMD_TOKEN /srv/apexcore/cmd-api/.env 2>/dev/null | cut -d= -f2)

nohup python3 /srv/apexcore/cmd-api/hermes_dispatcher.py \
  >> /var/log/apexcore-dispatcher.log 2>&1 &

echo "Dispatcher PID: $!"

# Health check
curl http://localhost:7071/health

# Test-Dispatch
curl -s -X POST http://localhost:7071/dispatch \
  -H "Authorization: Bearer $DISPATCHER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task": "System status check"}' | python3 -m json.tool
```

---

## Open WebUI → Hermes → Dispatcher Integration

In Open WebUI kann der Dispatcher als Custom Tool oder via Hermes System-Prompt angesteuert werden:

**Option A — Direkt via n8n Webhook (empfohlen V1):**
- Operator schickt Task in Open WebUI an Hermes
- Hermes-System-Prompt enthält Routing-Instruktionen
- Hermes delegiert via Webhook an n8n → n8n → Dispatcher

**Option B — Dispatcher als separater OpenAI-kompatibler Endpoint (V2):**
- Dispatcher erhält OpenAI-API-Format direkt
- Klassifiziert intern und routet transparent
- Open WebUI spricht Dispatcher wie einen LLM an

V1 nutzt Option A. Option B erfordert OpenAI-API-kompatibles Wrapper-Layer im Dispatcher.

---

## Hinweis: cmd-api vs. Dispatcher

| Service | Port | Zweck |
|---|---|---|
| `cmd-api/server.py` | 7070 | Infrastruktur-Kontrolle: Caddy reload, Docker exec, Container-Status |
| `cmd-api/hermes_dispatcher.py` | 7071 | Intent-Routing: Task → Hermes / n8n / OpenClaw |

Beide Services sind voneinander unabhängig und können einzeln gestartet werden.
