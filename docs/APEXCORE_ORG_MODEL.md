# ApexCore — Organisationsmodell

_Rollen, Verantwortlichkeiten, Entscheidungsgrenzen und Routing-Logik_
_Dieses Dokument ist operativ — nicht philosophisch. Es definiert, wie reale Aufgaben fließen._

---

## Rollenübersicht

| Rolle | Entität | Typ | Level |
|---|---|---|---|
| **Founder / Human Owner** | Ich (oc@apexcore.group) | Human | 0 |
| **CEO / Control Plane** | Paperclip | AI System | 1 |
| **COO / CTO Orchestrator** | Hermes Agent | AI Agent | 2 |
| **Operations Worker** | OpenClaw | AI Agent | 3 |
| **Workflow Automation Worker** | n8n | Automation Engine | 3 |
| **Principal Engineering Worker** | Claude Code | AI Builder | 3 |
| **Knowledge & Status Registry** | Notion | External Service | — |
| **Operator Console** | Open WebUI | UI | — |

---

## Wer darf was — Entscheidungsgrenzen

### Founder (Human Owner)

- **Kann alles** — vollständige Override-Autorität
- Genehmigt Änderungen an Governance-Regeln
- Genehmigt neue Agenten / Rollenänderungen
- Genehmigt Budget-Caps und kritische externe Aktionen
- **Primärer Kanal:** Open WebUI → Hermes, oder direkt per SSH/CLI

### Paperclip (CEO-Layer, V2)

- Setzt übergeordnete Ziele (Goals/OKRs)
- Definiert und durchsetzt Governance-Regeln
- Überwacht Budget und Ressourcenverbrauch
- Eskaliert Anomalien an Founder
- **Handelt nicht selbst** — gibt Hermes Context und Constraints
- **In V1:** Paperclip-Rolle übernimmt der Founder manuell

### Hermes Agent (COO/CTO)

**Autonom erlaubt:**
- Aufgaben analysieren und in Subtasks zerlegen
- An n8n, OpenClaw, Claude Code delegieren
- Informationen recherchieren (OpenRouter/Kimi/Claude)
- Direkte Antworten auf Anfragen
- Status aus Notion lesen (via n8n)

**Requires Paperclip/Founder Review:**
- Externe Kommunikation außerhalb definierter Channels
- Entscheidungen über Budget oder kostenpflichtige Services
- Änderungen an der eigenen Konfiguration oder an anderen Agenten
- Aktionen mit Außenwirkung (Publizieren, Senden an Externe)

### OpenClaw (Operations Worker)

**Autonom erlaubt:**
- Nachrichten senden über WhatsApp/Telegram (wenn von Hermes beauftragt)
- Status-Updates senden
- Webhooks empfangen und weitergeben
- Interne Ops-Tasks ausführen

**Requires Hermes Delegation (keine Eigeninitiative):**
- Alle Aktionen nur auf Auftrag von Hermes
- Keine eigenständige Aufgabenaufnahme außer via Webhook/Trigger

### n8n (Workflow Automation Worker)

**Autonom erlaubt (wenn Workflow aktiv):**
- Cron-getriggerte Tasks ausführen
- Notion Tasks lesen und Status schreiben
- Hermes aufrufen mit definierten Prompts
- Heartbeat-Monitoring
- Audit-Log in Notion schreiben

**Requires Hermes oder Founder Trigger:**
- Neue Workflow-Aktivierung
- Workflows mit Außenwirkung (APIs, Messaging)

### Claude Code (Principal Engineering Worker)

**Autonom erlaubt:**
- Code lesen, analysieren, dokumentieren
- Refactoring ohne Breaking Changes
- Tests schreiben
- Dokumentation aktualisieren
- Fehlerbehebungen (bekannte, lokale Fehler)

**Requires Hermes oder Founder Freigabe:**
- Neue Features implementieren
- Compose-Dateien oder Deploy-Workflows ändern
- Externe Dependencies hinzufügen
- Commits auf main / PRs mergen

---

## Aufgaben-Routing

Welche Aufgabe geht wohin?

```
Aufgabentyp                 → Primärer Worker
────────────────────────────────────────────────────────────────
Recherche / Analyse         → Hermes (direkt, OpenRouter)
Strukturierter Report       → Hermes → Notion (via n8n)
Automation / Cron           → Hermes → n8n
Messenger-Nachricht senden  → Hermes → OpenClaw
Webhook empfangen           → OpenClaw → Hermes (oder n8n)
Code schreiben / fixen      → Hermes → Claude Code
Status in Notion schreiben  → n8n (direkt oder via Hermes)
Status aus Notion lesen     → n8n → Hermes (oder direkt)
Alert senden (System-Down)  → n8n → OpenClaw
Governance-Entscheidung     → Paperclip → Founder (eskaliert)
Neue Agent-Registrierung    → Paperclip (V2) oder Founder manuell (V1)
```

---

## Kommunikations-Matrix

| Von \ Nach | Paperclip | Hermes | OpenClaw | n8n | Claude Code | Notion | Open WebUI |
|---|---|---|---|---|---|---|---|
| **Founder** | Direct | Open WebUI | — | — | SSH/CLI | Direct | Direct |
| **Paperclip** | — | Directive API | — | Webhook | — | Read/Write | — |
| **Hermes** | Status Report | — | REST `/send` | Webhook | (via CI/CD) | via n8n | Response |
| **OpenClaw** | — | Webhook | — | Webhook | — | — | — |
| **n8n** | — | LiteLLM API | REST | — | — | Notion API | — |
| **Claude Code** | — | (async) | — | — | — | — | — |

---

## Approval-Queue V1 (manuell, bis Paperclip V2 aktiv)

Bis Paperclip live ist, läuft die Approval-Logik manuell:

1. Hermes erkennt eine Aktion, die Review braucht
2. Hermes schreibt den Task in Notion mit Status `Awaiting Approval`
3. n8n sendet via OpenClaw eine Telegram/WhatsApp-Notification
4. Founder genehmigt in Notion (Status → `Approved`)
5. n8n-Trigger erkennt Statuswechsel und führt die Aktion aus

Dieses Flow ist in `n8n-workflows/` als Template vorbereitet.

---

## Eskalations-Protokoll

| Situation | Wer eskaliert | An wen | Kanal |
|---|---|---|---|
| Service down > 5 Min | n8n (Heartbeat) | Founder | OpenClaw → Telegram |
| API-Budget-Warning | Hermes | Founder | Open WebUI + Notion |
| Unklare Aufgabe | Hermes | Founder | Open WebUI Antwort |
| Approval benötigt | Hermes | Founder | Notion + Telegram |
| Deploy fehlgeschlagen | GitHub Actions | Founder | GitHub Notification |
