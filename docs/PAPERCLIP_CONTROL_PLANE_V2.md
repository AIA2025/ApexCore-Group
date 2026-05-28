# Paperclip — Control Plane V2 Architecture

_Zielarchitektur für die Management- und Governance-Schicht von ApexCore_
_Status: V2-Planung | Implementierung: nach V1-Stabilisierung_

---

## Überblick

Paperclip ist die **Company Layer** von ApexCore — die einzige Schicht, die einen vollständigen Überblick über alle laufenden Agenten, offenen Ziele, Budget-Verbräuche und Governance-Prozesse hat.

Während Hermes operativ arbeitet (Aufgaben ausführen, delegieren, koordinieren), arbeitet Paperclip auf einer höheren Abstraktionsebene: Welche Ziele soll das System verfolgen? Wer darf was entscheiden? Welche Ressourcen werden verbraucht? Wo laufen Prozesse aus dem Ruder?

**Kernprinzip:** Paperclip steuert NICHT direkt die Agenten. Es setzt Rahmenbedingungen, Prioritäten und Limits — und Hermes exekutiert darin.

---

## Architektur-Position

```
┌────────────────────────────────────────────────────────────────┐
│                    PAPERCLIP (Control Plane)                    │
│   Goals │ Org-Chart │ Budget │ Governance │ Audit │ Reporting  │
└───────────────────────────┬────────────────────────────────────┘
                            │ Directives / Context
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                    HERMES (Operational Layer)                   │
│         Orchestrator │ Task Decomposition │ Delegation         │
└────────┬──────────────┬───────────────────┬────────────────────┘
         │              │                   │
    ┌────▼───┐    ┌──────▼──────┐    ┌──────▼───────┐
    │OpenClaw│    │     n8n     │    │  Claude Code │
    │  Ops   │    │ Automation  │    │  Engineering │
    └────────┘    └──────┬──────┘    └──────────────┘
                         │
                  ┌──────▼──────┐
                  │   Notion    │
                  │  (Storage)  │
                  └─────────────┘
```

---

## Komponenten von Paperclip V2

### 1. Company Layer / Org-Chart

Paperclip hält die vollständige Organisationsstruktur:

```yaml
org_structure:
  founder:
    name: "Human Owner"
    level: 0
    authority: "full override"
  agents:
    - id: paperclip
      role: "CEO / Control Plane"
      level: 1
      reports_to: founder
    - id: hermes
      role: "COO / CTO Orchestrator"
      level: 2
      reports_to: paperclip
    - id: openclaw
      role: "Operations Worker"
      level: 3
      reports_to: hermes
    - id: n8n
      role: "Workflow Automation Worker"
      level: 3
      reports_to: hermes
    - id: claude-code
      role: "Principal Engineering Worker"
      level: 3
      reports_to: hermes
```

Dieser Org-Chart wird in Notion gespiegelt (via n8n) und dient als Grundlage für Routing-Entscheidungen.

### 2. Goals & Objectives

Paperclip verwaltet übergeordnete Ziele (OKR-ähnlich) und macht sie für Hermes zugänglich:

```
Quarterly Goals
  └─ Goal: "Launch Creator OS V1"
       ├─ KR1: All V1 services running and stable (owner: Hermes)
       ├─ KR2: Notion task sync active (owner: n8n)
       └─ KR3: First 3 workflows automated (owner: n8n)
```

Hermes erhält beim Start eines Tasks den aktuellen Goal-Context von Paperclip, um Prioritäten zu setzen.

### 3. Budget & Resource Management

Paperclip trackt:
- **API-Kosten** (OpenRouter Token-Verbräuche pro Agent/Tag/Monat)
- **Task-Volumen** (Wie viele Tasks hat Hermes in welcher Zeit verarbeitet?)
- **Fehlerquoten** pro Service

Limites (v.a. API-Kosten) können als Hard-Caps oder Soft-Warnings konfiguriert werden. Bei Überschreitung: Hermes erhält ein "budget warning" Directive und reduziert die Nutzung teurer Modelle.

### 4. Governance & Approval

Paperclip definiert, welche Aktionen autonomes Ausführen erlaubt ist und welche Review brauchen:

```yaml
governance_rules:
  autonomous:
    - "draft content"
    - "read from notion"
    - "send status update via openclaw"
    - "run analysis"
    - "create n8n workflow"
  requires_review:
    - "publish content"
    - "delete data"
    - "send external email/message"
    - "make purchases or financial decisions"
    - "modify governance rules"
  requires_founder_approval:
    - "change agent roles"
    - "add new agents"
    - "modify budget caps"
    - "access sensitive credentials"
```

Hermes prüft vor der Delegation, ob eine Aktion im autonomen Bereich liegt. Falls nicht, legt er sie in eine Approval-Queue in Notion.

### 5. Audit Trail

Jede Agent-Aktion wird geloggt:
- Welcher Agent (Hermes, OpenClaw, n8n, Claude Code)
- Welche Aktion
- Timestamp
- Ergebnis (success/fail)
- Kosten (wenn API-Call)

Ziel: n8n schreibt jede Aktion in eine dedizierte Notion-Datenbank "Audit Log".

### 6. Worker Registration

Jeder Agent registriert sich beim Start bei Paperclip:

```json
{
  "agent_id": "hermes",
  "version": "1.0",
  "capabilities": ["orchestrate", "decompose_tasks", "delegate"],
  "api_endpoint": "http://hermes-agent:4000/v1",
  "heartbeat_interval": 60
}
```

Paperclip hält eine Agent-Registry. Wenn ein Agent ausfällt, kann Paperclip (oder n8n als Proxy) eine Alert-Action triggern.

### 7. Heartbeat & Status Reporting

Jeder Agent sendet alle 60 Sekunden einen Heartbeat an Paperclip (via n8n Webhook):

```json
{
  "agent_id": "hermes",
  "status": "running",
  "last_task": "task-id-xyz",
  "queue_depth": 3,
  "api_calls_today": 47
}
```

n8n überwacht Heartbeats und triggert Alerts (OpenClaw → Telegram) wenn ein Agent ausbleibt.

---

## Beziehungen zu anderen Services

| Service | Beziehung zu Paperclip |
|---|---|
| **Hermes** | Empfängt Goal-Context und Governance-Directives. Meldet Task-Status zurück. |
| **OpenClaw** | Führt Paperclip-Anweisungen zu Messaging (Status-Updates, Alerts) aus. |
| **n8n** | Brücke zwischen Paperclip und allen anderen Services. Schreibt Audit-Log, verteilt Heartbeat-Daten. |
| **Claude Code** | Meldet Build/Deploy-Status. Empfängt Engineering-Directives von Hermes (delegiert von Paperclip). |
| **Notion** | Primäres Speicherziel für Goals, Org-Chart, Audit-Log, Budget-Reports. |
| **Open WebUI** | Zeigt Operator den Paperclip-Status auf Anfrage. Kein direkter API-Kanal V1. |

---

## Technische Implementierung V2

Paperclip V2 wird als eigenständiger Service implementiert. Optionen:

| Option | Pro | Contra |
|---|---|---|
| Custom FastAPI Service | Vollständige Kontrolle | Mehr Dev-Aufwand |
| Notion als Backend + n8n als Trigger | Schnell, kein neuer Service | Begrenzte Real-time-Fähigkeit |
| Low-Code App (e.g. Retool/Appsmith) | UI out of the box | Dependency auf externen Service |

**Empfehlung für V2 Start:** Notion als Paperclip-Datenbank + n8n als Event-Bus + minimal Python-API für Agent-Registration und Heartbeat-Empfang. Kein Over-Engineering. Wächst mit dem System.

---

## Aktivierungs-Checkliste (vor V2 Go-Live)

- [ ] V1 Services alle stabil (Hermes, n8n, OpenClaw, Open WebUI)
- [ ] Notion Datenbank-Struktur definiert (Goals, Audit, Agents, Budget)
- [ ] n8n Heartbeat-Workflow aktiv
- [ ] Paperclip Image gebaut und getestet
- [ ] Governance-Regeln initial definiert
- [ ] Caddy: `paperclip.apexcore.group` aktivieren (503-Block entfernen)
- [ ] Automation-Stack: `--profile paperclip` testen
