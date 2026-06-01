# Caddy — Setup & Betrieb

_Reverse Proxy für ApexCore | Automatisches TLS via Let's Encrypt_

---

## Wie Caddy funktioniert

Caddy ist der einzige öffentliche Eintrittspunkt für alle Services.
Er terminiert TLS (HTTPS) automatisch und routet Requests an interne Docker-Container.

```
Internet → Caddy (Port 80/443) → Docker-Netz → Service-Container
```

TLS-Zertifikate werden automatisch über Let's Encrypt bezogen und erneuert.
Kein manuelles certbot, kein nginx, kein Zertifikatschaos.

---

## Benötigte DNS-Einträge

Alle Subdomains müssen als A-Records auf die VPS-IP zeigen: `76.13.138.73`

| Subdomain | Zweck |
|---|---|
| `ai.apexcore.group` | Open WebUI (primäres Frontend) |
| `hermes.apexcore.group` | Hermes WebUI (Agent-Control) |
| `n8n.apexcore.group` | n8n (Workflow-Automation) |
| `ops.apexcore.group` | OpenClaw (Ops/Messenger Agent) |
| `dashboard.apexcore.group` | Status-Dashboard |
| `openwebui.apexcore.group` | Redirect → ai.apexcore.group |
| `oc.apexcore.group` | OpenClaw Legacy-Domain |
| `paperclip.apexcore.group` | Paperclip (V2, derzeit 503) |

DNS wird automatisch via Porkbun API im GitHub Actions Deploy gesetzt.
Manueller Check: `dig ai.apexcore.group A`

---

## Caddy starten

```bash
cd /srv/apexcore
docker compose -f infra-compose/docker-compose.yml up -d
```

**Wichtig:** ai-stack und automation-stack müssen zuerst laufen (ihre Netzwerke werden benötigt).
Nutze stattdessen `scripts/stack-start.sh` für den richtigen Start in einem Schritt.

---

## Caddy neu laden (nach Caddyfile-Änderung)

```bash
# Config validieren
docker exec caddy caddy validate --config /etc/caddy/Caddyfile

# Reload (kein Downtime, kein Restart nötig)
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

Über cmd-api (aus einem Script):
```bash
curl -X POST http://localhost:7070/caddy/reload \
  -H "Authorization: Bearer $CMD_TOKEN"
```

---

## Caddyfile-Standort

| Umgebung | Pfad |
|---|---|
| Im Repo | `infra-compose/Caddyfile` |
| Auf dem VPS | `/srv/apexcore/infra-compose/Caddyfile` |
| Im Container | `/etc/caddy/Caddyfile` (gemountet) |
| Backup (alt) | `/opt/openclaw/reverse-proxy/Caddyfile.bak.*` |

---

## Wie Docker-Routing funktioniert

Caddy ist Mitglied in drei Netzwerken: `infra_net`, `ai_net`, `automation_net`.
Innerhalb dieser Netze kann Caddy Container über ihren Namen (Docker DNS) ansprechen.

Beispiel aus der Caddyfile:
```
ai.apexcore.group {
    reverse_proxy open-webui:8080
}
```

`open-webui` wird von Docker DNS auf die Container-IP im `ai_net` aufgelöst.
Kein Port-Forwarding auf den Host nötig.

---

## TLS / HTTPS

- Caddy holt Zertifikate automatisch via Let's Encrypt ACME
- ACME-Challenge läuft über Port 80 (muss offen sein)
- Zertifikate werden in Volume `caddy_data` gespeichert (persistent)
- Automatische Erneuerung, kein manueller Eingriff nötig

**E-Mail für Let's Encrypt** in `infra-compose/.env`:
```
CADDY_EMAIL=admin@apexcore.group
```

---

## Was NICHT öffentlich sein sollte

Diese Ports dürfen NIE direkt exposed werden (kein Firewall-Port-Freigabe):

| Port | Service | Warum intern |
|---|---|---|
| 4000 | hermes-agent (LiteLLM) | Admin-API, API-Keys |
| 11434 | ollama | Keine Auth, freier Modell-Zugriff |
| 5678 | n8n | Credential-Store, Webhook-Secrets |
| 7070 | cmd-api | Shell-Zugriff auf VPS |
| 3001 | hermes-webui | Nur für Admin-Nutzung |

Firewall-Regel (ufw): nur 22 (SSH), 80, 443 öffentlich.
