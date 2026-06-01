# Paperclip — V1 Vorbereitung

_Was in V1 vorbereitet ist, warum Paperclip noch nicht als Runtime-Controller aktiv ist,
und was erfüllt sein muss, bevor V2 gestartet wird._

---

## Rolle von Paperclip im Gesamtsystem

Paperclip ist nicht ein weiteres Tool — es ist die **Control Plane** des gesamten Multi-Agent-Systems.
Während Hermes operativ arbeitet (Aufgaben ausführen, delegieren), steuert Paperclip auf Management-Ebene:
Goals, Governance, Budget, Org-Chart, Reporting.

Vollständige Architektur-Beschreibung: [`docs/PAPERCLIP_CONTROL_PLANE_V2.md`](PAPERCLIP_CONTROL_PLANE_V2.md)

---

## Warum Paperclip in V1 nicht als Full Runtime Controller aktiv ist

Eine Control Plane, die auf einem instabilen Stack aufsetzt, ist wertlos.

Konkret: Wenn Hermes, n8n und Notion noch nicht stabil laufen und definierte APIs haben, kann Paperclip:
- keine verlässlichen Heartbeats empfangen
- keine sinnvollen Budget-Daten aggregieren
- keine Governance-Regeln durchsetzen (die darunter liegenden Services kennen sie nicht)
- keine Goals tracken, die kein System zuverlässig reported

Paperclip zu früh zu aktivieren bedeutet: ein Management-Dashboard über einem halb funktionierenden Stack — das ist schlechter als gar keins, weil es falsches Vertrauen erzeugt.

**Grundsatz:** Die operative Basis muss funktionieren, bevor die Governance-Schicht darüberkommt.

---

## Was in V1 bereits für Paperclip vorbereitet ist

### Infrastruktur
- [x] DNS `paperclip.apexcore.group` eingerichtet (Porkbun A-Record)
- [x] Caddy-Entry angelegt (gibt 503 mit erklärendem Text bis Aktivierung)
- [x] `paperclip` Service in `automation-stack/docker-compose.yml` als Compose-Profile konfiguriert
- [x] Volume `paperclip_data` definiert
- [x] Port `3002` auf Host reserviert (Container-Port: 80)

### Dokumentation
- [x] Vollständige V2-Zielarchitektur in `PAPERCLIP_CONTROL_PLANE_V2.md`
- [x] Org-Modell mit Rollen, Entscheidungsgrenzen, Routing in `APEXCORE_ORG_MODEL.md`
- [x] Approval-Queue-Flow für V1 (manuell via Notion + n8n) dokumentiert

### n8n-Vorbereitung
- [x] n8n-Workflow-Template `n8n_notion_task_sync_v1.json` als Basis für spätere Paperclip-Integration
- [x] Heartbeat-Monitoring Workflow (`03-heartbeat-monitor.json`) als Vorläufer von Paperclip-Heartbeats

---

## Voraussetzungen für Paperclip V2 Aktivierung

Alle Punkte müssen erfüllt sein:

### Technisch
- [ ] Open WebUI stabil und über `ai.apexcore.group` erreichbar
- [ ] Hermes Agent stabil, `/v1/models` antwortet korrekt
- [ ] n8n aktiv mit mindestens 2 laufenden Workflows (Notion-Sync, Heartbeat)
- [ ] OpenClaw aktiv (echtes Image, nicht Placeholder)
- [ ] Notion-Credentials in n8n eingetragen und funktional getestet
- [ ] Paperclip-Image existiert und ist buildbar (kein Placeholder)
- [ ] Paperclip kennt Endpoints aller Services (via Config oder Service-Discovery)

### Inhaltlich
- [ ] Notion-Datenbankstruktur vollständig angelegt: Goals, Audit-Log, Agent-Registry, Budget
- [ ] Governance-Regeln initial definiert und in Paperclip-Config eingetragen
- [ ] Mindestens 1 vollständiger End-to-End-Workflow läuft (Notion Task → Hermes → Status-Update)
- [ ] Budget-Caps für OpenRouter definiert

---

## Aktivierung (wenn alle Voraussetzungen erfüllt)

```bash
# 1. Echtes Image in automation-stack/.env setzen
PAPERCLIP_IMAGE=ghcr.io/aia2025/paperclip:latest

# 2. Caddyfile: 503-Block durch reverse_proxy ersetzen
# paperclip.apexcore.group {
#   reverse_proxy paperclip:80
# }

# 3. Caddy validate + reload
docker exec caddy caddy validate --config /etc/caddy/Caddyfile
docker exec caddy caddy reload --config /etc/caddy/Caddyfile

# 4. Paperclip-Profil starten
cd /srv/apexcore
docker compose -f automation-stack/docker-compose.yml --profile paperclip up -d

# 5. Healthcheck
/srv/apexcore/scripts/healthcheck.sh
```

---

## Was Paperclip später an anderen Services anbindet

| Integration | Wie | Zweck |
|---|---|---|
| Hermes | REST API (LiteLLM `/v1`) | Goal-Context senden, Status empfangen |
| n8n | Webhook-Trigger | Events senden/empfangen, Audit-Log schreiben lassen |
| OpenClaw | REST `/send` | Alerts und Notifications senden |
| Notion | Notion API (direkt oder via n8n) | Goals, Org-Chart, Budget, Audit-Log |
| Open WebUI | (kein direkter Kanal V1) | Operator kann Paperclip-Status via Hermes abrufen |
| Claude Code | (via Hermes Delegation) | Engineering-Tasks als strukturierte Hermes-Requests |
