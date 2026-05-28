# ApexCore Orchestration V1

_Architektur-Definition | Stand: 2026-05-28_

---

## Rollen-Übersicht

| Komponente | Typ | Rolle |
|---|---|---|
| **Open WebUI** | UI / Frontend | Primäre Operator-Oberfläche für Chats, Task-Eingabe, Modell-Wechsel |
| **Hermes Agent** | Orchestrator | LLM-Gateway (OpenAI-kompatibel) + COO/CTO-Agent; verteilt Tasks an Tools/Worker |
| **Hermes WebUI** | UI / Admin | Separate Open-WebUI-Instanz, exklusiv auf Hermes zeigend; für Prompt-Design und Agent-Config |
| **OpenClaw** | Action Worker | Ops-Agent; empfängt/sendet WhatsApp & Telegram, führt Aktionen aus, exponiert REST-API |
| **n8n** | Automation Layer | Cron-Jobs, Pipelines, Notion-Sync, Webhook-Receiver; bindet alle Systeme zusammen |
| **Ollama** | LLM Worker | Lokale Modell-Inferenz; Fallback und private Modelle, optional abschaltbar |
| **OpenRouter** | LLM Provider (extern) | Cloud-Modelle (Claude, Kimi, GPT-4o etc.); primäre Modellquelle für Hermes |
| **Notion** | Storage / Knowledge | Aufgaben-DB, Dokumentation, Status-Tracking; kein aktiver Service, nur API-Ziel |
| **Caddy** | Infra | Reverse Proxy; TLS-Terminierung, Domain-Routing, einziger öffentlicher Eintrittspunkt |
| **Paperclip** | Management (V2) | Org-Chart, Prozess-Management; in V1 vorbereitet aber inaktiv |

---

## Daten- und Steuerfluss

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Internet / User                               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTPS
                    ┌──────▼──────┐
                    │    Caddy    │  TLS-Terminierung
                    │  (infra)    │  Domain-Routing
                    └──┬───┬───┬──┘
                       │   │   │
          ─────────────┘   │   └─────────────────────────────
         │                 │                                  │
   ┌─────▼──────┐    ┌─────▼──────┐                  ┌──────▼──────┐
   │ open-webui │    │hermes-webui│                  │    n8n      │
   │ (Frontend) │    │ (Admin UI) │                  │(Automation) │
   └─────┬──────┘    └──────┬─────┘                  └──────┬──────┘
         │                  │                               │     │
         │     ┌────────────▼────────────┐                 │     │
         └────►│    hermes-agent         │◄────────────────┘     │
               │ (LiteLLM / OpenAI API)  │                        │
               └────────────┬────────────┘                        │
                             │                                     │
                   ┌─────────▼─────────┐              ┌──────────▼───────┐
                   │   OpenRouter      │              │    Notion API     │
                   │ (Claude, Kimi...) │              │  (extern, HTTPS)  │
                   └───────────────────┘              └──────────────────┘
                                                               │
                                                   ┌──────────▼───────────┐
                                                   │      openclaw        │
                                                   │  (WhatsApp/Telegram) │
                                                   └──────────────────────┘
```

---

## Kommunikations-Protokolle

| Verbindung | Protokoll | Endpoint |
|---|---|---|
| Open WebUI → Hermes Agent | OpenAI-compatible REST | `http://hermes-agent:4000/v1` |
| Hermes WebUI → Hermes Agent | OpenAI-compatible REST | `http://hermes-agent:4000/v1` |
| Hermes Agent → OpenRouter | OpenAI-compatible REST | `https://openrouter.ai/api/v1` |
| Open WebUI → Ollama | Ollama REST | `http://ollama:11434` |
| n8n → Hermes Agent | OpenAI-compatible REST | `http://hermes-agent:4000/v1` |
| n8n → Notion | Notion REST API | `https://api.notion.com/v1` |
| n8n → OpenClaw | REST | `http://openclaw:8000` |
| External → n8n Webhooks | HTTPS | `https://n8n.apexcore.group/webhook/*` |

---

## Netzwerk-Isolation

```
infra_net          ← Caddy intern
ai_net             ← open-webui, hermes-agent, hermes-webui, ollama, openclaw
automation_net     ← n8n, paperclip

Caddy ist Mitglied in: infra_net + ai_net + automation_net
ai_net ↔ automation_net: KEINE direkte Verbindung
```

**Cross-Stack-Kommunikation** (n8n → Hermes, n8n → OpenClaw):
n8n greift auf Hermes und OpenClaw über ihre FQDN-URLs zu, weil diese in verschiedenen Netzen liegen. In V2 kann ein gemeinsames Bridge-Netz eingeführt werden, wenn die Latenz relevant wird.

---

## Ziel-URLs V1

| URL | Service | Intern |
|---|---|---|
| `ai.apexcore.group` | Open WebUI | `open-webui:8080` |
| `hermes.apexcore.group` | Hermes WebUI | `hermes-webui:8080` |
| `n8n.apexcore.group` | n8n | `n8n:5678` |
| `ops.apexcore.group` | OpenClaw | `openclaw:8000` |
| `dashboard.apexcore.group` | Static Dashboard | file_server |
| `openwebui.apexcore.group` | → Redirect | → ai.apexcore.group |
| `oc.apexcore.group` | OpenClaw (legacy) | `openclaw:8000` |
| `paperclip.apexcore.group` | Placeholder (503) | aktiviert in V2 |

---

## Warum Paperclip in V1 inaktiv bleibt

Paperclip soll als Management-/Org-Chart-Layer ÜBER alle anderen Systemen liegen.
Das setzt voraus, dass die darunter liegenden Systeme (Hermes, n8n, Notion, OpenClaw)
stabil laufen, dokumentiert sind und definierte APIs haben.

V1 legt die Grundlage. Paperclip aktivieren, bevor diese Basis steht, würde:
1. Architektur-Entscheidungen erzwingen, die auf wackeligen Fundamenten basieren
2. Debugging deutlich schwerer machen
3. Unnötige Abhängigkeiten einführen

Voraussetzungen für V2 / Paperclip-Aktivierung: siehe `docs/PAPERCLIP_PREP.md`.
