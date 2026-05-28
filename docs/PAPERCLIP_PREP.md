# Paperclip — Vorbereitung V1

_Warum Paperclip jetzt noch nicht aktiv ist — und was dafür erfüllt sein muss_

---

## Was Paperclip sein soll

Paperclip ist der **Management- und Org-Chart-Layer** über dem ApexCore-System.
Er visualisiert Strukturen, Prozesse, Verantwortlichkeiten und den Systemstatus auf
einer höheren Abstraktionsebene.

Paperclip kennt alle anderen Systeme — er liest aus Notion, fragt Hermes ab, zeigt n8n-Status —
aber er **steuert** sie in V1 noch nicht.

---

## Warum Paperclip in V1 inaktiv bleibt

Ein Org-Chart-/Management-Layer, der auf instabilen oder unvollständig konfigurierten
Systemen aufsetzt, ist nutzlos und erzeugt falsche Informationen.

Konkret: Wenn Hermes, n8n und Notion noch nicht stabil laufen, kann Paperclip
keine sinnvollen Status-Informationen anzeigen. Es wäre ein leeres Dashboard
über einem halb funktionierenden Stack.

**Grundsatz:** Erst die Basis stabilisieren, dann Sichtbarkeit draufsetzen.

---

## Voraussetzungen für Paperclip-Aktivierung

Alle folgenden Punkte müssen erfüllt sein:

### Technisch
- [ ] Open WebUI läuft stabil und ist über `ai.apexcore.group` erreichbar
- [ ] Hermes Agent läuft stabil (LiteLLM) und antwortet auf `/v1/models`
- [ ] n8n läuft und hat mindestens 1 aktiven Workflow
- [ ] Notion-Credentials in n8n eingetragen und getestet
- [ ] OpenClaw erreichbar auf `ops.apexcore.group`
- [ ] Paperclip-Image existiert (aktuell Placeholder)
- [ ] Paperclip kennt die API-Endpoints der anderen Services

### Inhaltlich
- [ ] Notion-Datenbank-Struktur definiert (Tasks, Projects, Status-Felder)
- [ ] Org-Chart / Rollenstruktur in Notion gepflegt
- [ ] Mindestens 1 vollständiger Workflow (Notion Task → Hermes → Status zurück) läuft

---

## V1 Vorbereitung (bereits erledigt)

- DNS `paperclip.apexcore.group` eingerichtet
- Caddy-Entry angelegt (gibt 503 bis Aktivierung)
- `paperclip` Service in `automation-stack/docker-compose.yml` als inaktives Profil vorbereitet
- Volume `paperclip_data` definiert

---

## Aktivierung (wenn bereit)

```bash
# 1. Echtes Image in automation-stack/.env eintragen:
PAPERCLIP_IMAGE=ghcr.io/aia2025/paperclip:latest

# 2. Caddyfile: paperclip.apexcore.group Block aktivieren (503-Zeile entfernen)

# 3. Stack mit Profil starten:
docker compose -f /srv/apexcore/automation-stack/docker-compose.yml \
  --profile paperclip up -d

# 4. Caddy reload
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```
