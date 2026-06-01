# ApexCore Orchestration V1

_Architektur-Definition | Stand: 2026-05-28_
_Was V1 heute real kann — V2-Zustand klar abgegrenzt._

---

## Rollen-Übersicht

| Komponente | Typ | Rolle in V1 |
|---|---|---|
| **Open WebUI** | Frontend | Primäre Operator-Konsole; Chat-Interface für Hermes und Ollama |
| **Hermes Agent** | Orchestrator | LLM-Gateway (OpenAI-kompatibel) + COO/CTO-Agent; delegiert Tasks an Worker |
| **Hermes WebUI** | Frontend (Admin) | Separate Open-WebUI-Instanz exklusiv auf Hermes; für Prompt-Design und Agent-Config |
| **OpenClaw** | Action Worker | Ops-Agent; WhatsApp/Telegram-Integration, externe Aktionen (V1: auf `ops` Profile) |
| **n8n** | Automation Layer | Cron-Jobs, Notion-Sync, Webhook-Receiver, Heartbeat-Monitoring |
| **Ollama** | LLM Worker | Lokale Modell-Inferenz; Fallback und private Modelle |
| **OpenRouter** | LLM Provider (extern) | Cloud-Modelle für Hermes (Claude, Kimi, GPT-4o etc.) |
| **Notion** | Storage | Aufgaben-DB, Status-Tracking, Dokumentation; kein Container, nur API-Ziel |
| **Caddy** | Infra | Reverse Proxy; TLS, Domain-Routing, einziger öffentlicher Eintrittspunkt |
| **Paperclip** | Control Plane (V2) | Governance, Goals, Org-Chart; in V1 vorbereitet, nicht aktiv |

---

## Daten- und Steuerfluss

```
User (Browser / Mobile)
        │ HTTPS
        ▼
    ┌───────┐
    │ Caddy │  TLS-Terminierung, Domain-Routing
    └───┬───┘
        │
   ─────┼──────────────────────────────────────
   │           │                    │
   ▼           ▼                    ▼
open-webui  hermes-webui          n8n
(ai_net)    (ai_net)          (automation_net
                               + ai_net)
   │           │                    │
   └─────┬─────┘                    │
         │                          │
         ▼                          │
   hermes-agent ◄───────────────────┘
   (LiteLLM, ai_net)
         │
         ▼
   OpenRouter API
   (Claude, Kimi, auto)
         │
   ┌─────┴────────┐
   │              │
   ▼              ▼
openclaw         n8n
(ai_net)     (via Webhook)
   │              │
   ▼              ▼
Messenger      Notion API
WA/Telegram    (extern)
```

---

## Kommunikations-Protokolle

| Verbindung | Protokoll | Endpoint | Netz |
|---|---|---|---|
| Open WebUI → Hermes Agent | OpenAI-REST | `http://hermes-agent:4000/v1` | ai_net |
| Hermes WebUI → Hermes Agent | OpenAI-REST | `http://hermes-agent:4000/v1` | ai_net |
| Hermes Agent → OpenRouter | OpenAI-REST | `https://openrouter.ai/api/v1` | extern |
| Open WebUI → Ollama | Ollama-REST | `http://ollama:11434` | ai_net |
| n8n → Hermes Agent | OpenAI-REST | `http://hermes-agent:4000/v1` | ai_net ✱ |
| n8n → OpenClaw | REST | `http://openclaw:8000` | ai_net ✱ |
| n8n → Notion | Notion-REST API | `https://api.notion.com/v1` | extern |
| External → n8n Webhooks | HTTPS | `https://n8n.apexcore.group/webhook/*` | extern |

**✱ Cross-Stack-Kommunikation:** n8n ist Mitglied in **both** `automation_net` (primary) und `ai_net` (external join), damit es direkt mit hermes-agent und openclaw kommunizieren kann. Abhängigkeit: ai-stack muss vor automation-stack gestartet werden.

---

## Netzwerk-Isolation

```
infra_net          ← Caddy intern
ai_net             ← open-webui, hermes-agent, hermes-webui, ollama, openclaw, n8n (join)
automation_net     ← n8n, paperclip

Caddy:             infra_net + ai_net + automation_net (alle drei)
n8n:               automation_net + ai_net (cross-join für direkte Agent-Kommunikation)
```

Dienste, die **nicht** in ai_net sind, können Hermes und OpenClaw **nicht** direkt erreichen.

---

## Ziel-URLs V1

| URL | Service | Container:Port |
|---|---|---|
| `ai.apexcore.group` | Open WebUI | `open-webui:8080` |
| `hermes.apexcore.group` | Hermes WebUI | `hermes-webui:8080` |
| `n8n.apexcore.group` | n8n | `n8n:5678` |
| `ops.apexcore.group` | OpenClaw | `openclaw:8000` |
| `dashboard.apexcore.group` | Static Dashboard | Caddy file_server |
| `openwebui.apexcore.group` | → Redirect | → ai.apexcore.group |
| `oc.apexcore.group` | OpenClaw (Legacy) | `openclaw:8000` |
| `paperclip.apexcore.group` | 503 Placeholder | aktiviert in V2 |

---

## Was V1 wirklich kann (ehrlich)

| Fähigkeit | Status | Voraussetzung |
|---|---|---|
| Open WebUI → LLM Chat via Hermes | ✅ | OPENROUTER_API_KEY + LITELLM_MASTER_KEY gesetzt |
| Open WebUI → Ollama (lokale Modelle) | ✅ | Ollama läuft; Modell heruntergeladen mit `docker exec ollama ollama pull <model>` |
| Hermes WebUI (separate Admin-UI) | ✅ | Gleiche Voraussetzung wie oben |
| n8n Workflows | ✅ | N8N_BASIC_AUTH_PASSWORD + N8N_ENCRYPTION_KEY gesetzt |
| n8n → Notion Sync | ✅ | Notion-Credentials in n8n eingetragen |
| n8n → Hermes API-Call | ✅ | LITELLM_MASTER_KEY in automation-stack/.env |
| OpenClaw (Messenger) | ⚠️ V1 prepared | OPENCLAW_IMAGE muss gesetzt sein; `--profile ops` |
| Caddy TLS | ✅ | DNS zeigt auf VPS, Port 80+443 offen |
| Paperclip | ❌ V2 | Alle Voraussetzungen in PAPERCLIP_PREP.md |

---

## Was V2 bringt (abgegrenzt)

- Paperclip als vollständige Control Plane (Goals, Budget, Governance, Audit)
- Memory-Layer für Hermes (persistenter Kontext über Sessions)
- Agent Function-Calling (Hermes ruft n8n / OpenClaw direkt als Tools)
- Vollständiges Heartbeat-/Health-Monitoring via Paperclip
- Approval-Queue via Paperclip (nicht mehr manuell via Notion)
- Org-Chart in Paperclip UI sichtbar (nicht nur in Markdown)

Details: [`docs/PAPERCLIP_CONTROL_PLANE_V2.md`](PAPERCLIP_CONTROL_PLANE_V2.md)
