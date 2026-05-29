# ApexCore — VPS Stack

**VPS:** 76.13.138.73 (Ubuntu 22.04, Hostinger KVM 8)

## Aktive Services & Ports

| Service | Port | URL | Status |
|---|---|---|---|
| n8n (produktiv) | 5678 | http://76.13.138.73:5678 | ✅ aktiv |
| Open WebUI | 3000 | http://76.13.138.73:3000 | ✅ aktiv |
| Hermes WebUI | 32772 | http://76.13.138.73:32772 | ✅ aktiv |
| Hermes Agent | 8642 | intern | ✅ aktiv |
| Ollama API | 32768 | intern | ✅ aktiv |
| Paperclip | 52309 | http://76.13.138.73:52309 | ✅ aktiv |
| ApexCore Website | 3011 | http://76.13.138.73:3011 | ✅ aktiv |
| Operator Dashboard | 9090 | http://76.13.138.73:9090 | ✅ aktiv |
| OpenClaw | 45261 | http://76.13.138.73:45261 | ✅ aktiv |

## Geplante Subdomains (nach DNS-Setup)

| Subdomain | Ziel |
|---|---|
| openwebui.apexcore.group | :3000 |
| n8n.apexcore.group | :5678 |
| hermes.apexcore.group | :32772 |
| paperclip.apexcore.group | :52309 |
| dashboard.apexcore.group | :9090 |

→ Caddyfile liegt im Repo: `Caddyfile`

## n8n Instanzen

- **Port 5678** (`n8n` Container) — PRODUKTIV: Claude Webhook, Notion Logger, Heartbeat Monitor
- **Port 5679** (`n8n-lx1z-n8n-1`) — GESTOPPT / nicht mehr benötigt

## n8n Workflows (aktiv)

| Workflow | ID | Trigger |
|---|---|---|
| Claude Webhook | dQhE0mzXP0BlvlKt | POST /webhook/claude |
| Notion Logger | QR8IldDUDuhRHW7r | POST /webhook/log |
| Heartbeat Monitor | 8SAHX9kl2oLba5h8 | Alle 12h automatisch |

## Wichtige Pfade

| Was | Pfad |
|---|---|
| Setup-Script | /opt/apexcore/setup-complete.sh |
| Operator Dashboard | /opt/apexcore-dashboard/index.html |
| n8n DB Backup | /root/backups/n8n_database_*.sqlite |
| Open WebUI DB | /var/lib/docker/volumes/open-webui/_data/webui.db |
| Hermes SOUL.md | /root/.hermes/SOUL.md |
| Notion Backup Script | /root/scripts/notion-backup.sh |

## Credentials (ENV-Referenz)

Credentials werden **nicht** im Repo gespeichert.
Siehe `/root/.hermes/.env` und n8n Credentials-UI.
