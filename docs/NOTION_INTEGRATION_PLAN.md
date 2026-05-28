# Notion Integration Plan V1

_Wie ApexCore mit Notion kommuniziert_

---

## Architektur

Notion ist **kein aktiver Service** — es gibt keinen Notion-Container.
Alles läuft über die Notion REST API via n8n.

```
n8n → Notion API (https://api.notion.com/v1)
         ├─ Tasks lesen      (Database query)
         ├─ Status schreiben (Page update)
         ├─ Logs anlegen     (Page create)
         └─ Dokumente lesen  (Block read)
```

---

## Setup (einmalig in n8n)

### 1. Notion Integration erstellen

1. Gehe zu https://www.notion.so/my-integrations
2. Neue Integration anlegen: "ApexCore n8n"
3. Type: Internal
4. Capabilities: Read/Write Content, Read/Write User Info (optional)
5. **Integration Token** kopieren

### 2. Token in n8n eintragen

1. n8n öffnen: https://n8n.apexcore.group
2. Settings → Credentials → New Credential
3. Typ: "Notion API"
4. API Key eintragen
5. Name: "Notion API" (damit Workflow-Templates funktionieren)

### 3. Datenbank mit Integration verbinden

1. In Notion: Tasks-Datenbank öffnen
2. Settings (…) → Add Connections → ApexCore n8n
3. Datenbank-ID aus URL kopieren: `notion.so/XXXX?v=...` → `XXXX` = DB-ID

---

## Empfohlene Notion-Datenbank-Struktur (Tasks)

| Feld | Typ | Werte |
|---|---|---|
| Name | Title | Aufgabentitel |
| Status | Select | `Todo` / `In Progress` / `Done` / `Blocked` |
| Assigned To | Select | `Hermes` / `n8n` / `Human` |
| Priority | Select | `High` / `Medium` / `Low` |
| Due Date | Date | Fälligkeitsdatum |
| Hermes Note | Rich Text | Antwort/Notiz von Hermes |
| Source | Select | `Manual` / `n8n` / `OpenClaw` |

---

## Workflow-Templates

Alle Templates liegen in `automation-stack/templates/`.

| Datei | Zweck | Import-Pfad |
|---|---|---|
| `n8n_notion_task_sync_v1.json` | Tasks aus Notion lesen, mit Hermes verarbeiten, Status updaten | n8n → Workflows → Import |

### n8n_notion_task_sync_v1 — Was er tut

1. Alle 30 Minuten ausgeführt
2. Liest alle Tasks mit Status `Todo` aus der Notion-DB
3. Sendet jeden Task an Hermes Agent (`/v1/chat/completions`)
4. Setzt Status auf `In Progress`
5. Schreibt Hermes-Antwort in das Feld `Hermes Note`

### Nach dem Import anpassen

1. `__NOTION_ID__` → ID der Notion-Credentials in n8n
2. `__NOTION_TASKS_DB_ID__` → ID der Tasks-Datenbank
3. Workflow aktivieren (Toggle oben rechts)

---

## Erweiterte Workflows (V2)

| Workflow | Beschreibung |
|---|---|
| Notion → OpenClaw | Neue Tasks als WhatsApp/Telegram-Notification |
| Done-Tasks → Archiv | Abgeschlossene Tasks in Archiv-DB verschieben |
| Weekly Report | Wöchentliche Zusammenfassung aus Notion generieren und senden |
| Hermes → Notion | Hermes schreibt Erkenntnisse direkt in Notion-Dokumente |

---

## Bestehende n8n-Workflows (aus Repo)

Diese Workflows existieren bereits und können importiert werden:

| Datei | Funktion |
|---|---|
| `n8n-workflows/01-claude-webhook.json` | Webhook → Claude API → Response |
| `n8n-workflows/02-notion-logger.json` | Webhook → Notion Page erstellen |
| `n8n-workflows/03-heartbeat-monitor.json` | Heartbeat-Monitoring |

Import: n8n → Workflows → Import from File
