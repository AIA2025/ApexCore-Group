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

## Datenbank-Schemas V1

Alle Datenbanken verwenden dasselbe Status-Set:
`Todo` / `In Progress` / `Done` / `Blocked` / `Awaiting Approval` / `Archived`

---

### Tasks (Kern-Aufgaben-Queue)

| Feld | Typ | Werte / Format |
|---|---|---|
| Name | Title | Aufgabentitel |
| Status | Select | `Todo` / `In Progress` / `Done` / `Blocked` / `Awaiting Approval` |
| Intent | Select | `RESEARCH` / `PRODUCT` / `CONTENT` / `CLIENT` / `ADMIN` / `SYSTEM` |
| Assigned To | Select | `Hermes` / `n8n` / `Human` / `OpenClaw` / `Claude Code` |
| Priority | Select | `High` / `Medium` / `Low` |
| Due Date | Date | ISO 8601 |
| Source | Select | `Manual` / `Webhook` / `n8n` / `Dispatcher` |
| Task ID | Rich Text | task_id aus Dispatcher (z.B. `a3f9c1b2`) |
| Hermes Note | Rich Text | LLM-Antwort / Ergebnis |
| Created | Created Time | automatisch |

---

### Produkt-Datenbank

| Feld | Typ | Werte / Format |
|---|---|---|
| Name | Title | Produktname |
| Status | Select | `Idea` / `In Build` / `Ready` / `Live` / `Paused` / `Archived` |
| Revenue Type | Select | `Digital` / `Service` / `Subscription` / `Physical` |
| Price | Number | EUR |
| Platform | Multi-Select | `Shopify` / `Gumroad` / `Notion` / `Calendly` / `Custom` |
| Launch Date | Date | ISO 8601 |
| Revenue MTD | Number | EUR, monatlich aktualisiert |
| Notes | Rich Text | Sonstiges |
| Created | Created Time | automatisch |

---

### Revenue-Tracking

| Feld | Typ | Werte / Format |
|---|---|---|
| Entry | Title | Beschreibung (z.B. `Shopify Sale – ApexOS Pack`) |
| Amount | Number | EUR |
| Type | Select | `Sale` / `Subscription` / `Refund` / `Cost` |
| Source | Select | `Shopify` / `Manual` / `Stripe` / `PayPal` |
| Produkt | Relation | → Produkt-Datenbank |
| Date | Date | Buchungsdatum |
| Month | Formula | `formatDate(prop("Date"), "YYYY-MM")` |
| Created | Created Time | automatisch |

---

### Content-Pipeline

| Feld | Typ | Werte / Format |
|---|---|---|
| Title | Title | Content-Titel |
| Status | Select | `Idea` / `Draft` / `Review` / `Scheduled` / `Published` / `Archived` |
| Format | Select | `Post` / `Newsletter` / `Video` / `Short` / `Thread` / `Email` |
| Platform | Multi-Select | `Instagram` / `LinkedIn` / `YouTube` / `Newsletter` / `TikTok` |
| Publish Date | Date | geplantes Veröffentlichungsdatum |
| Assigned To | Select | `Hermes` / `Human` / `Codex` |
| Copy | Rich Text | Finaler Text |
| Notes | Rich Text | Briefing / Kontext |
| Created | Created Time | automatisch |

---

### Lead-Pipeline

| Feld | Typ | Werte / Format |
|---|---|---|
| Name | Title | Kontaktname |
| Status | Select | `New` / `Contacted` / `Qualified` / `Proposal` / `Won` / `Lost` |
| Company | Rich Text | Unternehmen |
| Channel | Select | `Inbound` / `Outbound` / `Referral` / `Event` |
| Value | Number | EUR, geschätzter Auftragswert |
| Next Action | Rich Text | nächster Schritt |
| Last Contact | Date | letztes Kontaktdatum |
| Notes | Rich Text | Gesprächsnotizen |
| Created | Created Time | automatisch |

---

### Audit Log (automatisch via n8n)

| Feld | Typ | Werte / Format |
|---|---|---|
| Entry | Title | `[task_id] [intent] [status]` |
| Task ID | Rich Text | aus Dispatcher |
| Intent | Select | `RESEARCH` / `PRODUCT` / `CONTENT` / `CLIENT` / `ADMIN` / `SYSTEM` |
| Status | Select | `DONE` / `BLOCKED` / `ROUTED` |
| Result Preview | Rich Text | erste 500 Zeichen der Antwort |
| Worker | Rich Text | z.B. `hermes-agent` |
| Timestamp | Date | ISO 8601 |
| Source | Select | `Dispatcher` / `n8n` / `Manual` |

---

### SOP-Dokumentation

| Feld | Typ | Werte / Format |
|---|---|---|
| Title | Title | SOP-Name |
| Category | Select | `Ops` / `Sales` / `Content` / `Tech` / `Finance` |
| Status | Select | `Draft` / `Active` / `Outdated` |
| Owner | Select | `Hermes` / `Human` / `n8n` |
| Last Updated | Last Edited Time | automatisch |
| Content | Rich Text | SOP-Text oder Link zu Page |

---

## Datenbank-Verlinkungen

```
Tasks ─────────────► Produkt-Datenbank   (Tasks.Produkt → Produkt)
Revenue-Tracking ──► Produkt-Datenbank   (Revenue.Produkt → Produkt)
Audit Log ─────────► Tasks              (über task_id, kein direkter Notion-Link in V1)
Content-Pipeline ──► (stand-alone, kein Link in V1)
Lead-Pipeline ─────► (stand-alone, kein Link in V1)
```

V2: Relations zwischen allen Datenbanken via Paperclip-konforme IDs.

---

## Einheitliche Status-Werte

Alle Agenten, n8n-Workflows und menschliche Bearbeiter verwenden dieselben Status-Labels:

| Status | Wer setzt ihn | Bedeutung |
|---|---|---|
| `Todo` | Mensch / n8n | Bereit zur Bearbeitung |
| `In Progress` | n8n / Hermes | Hermes oder Worker hat Task aufgenommen |
| `Done` | n8n / Dispatcher | Task abgeschlossen, Ergebnis vorhanden |
| `Blocked` | Dispatcher / Hermes | Fehler, manuelle Intervention nötig |
| `Awaiting Approval` | Hermes | Aktion braucht Founder-Freigabe |
| `Archived` | Mensch | Nicht mehr aktiv, bleibt erhalten |

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
