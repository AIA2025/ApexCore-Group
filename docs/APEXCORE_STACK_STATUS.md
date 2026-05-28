# ApexCore Stack Status

_Analysiert: 2026-05-28 | Quelle: Repo-Scan + deploy.yml + branch history_

---

## TL;DR — Was gefunden wurde

| Service | Status | Anmerkung |
|---|---|---|
| **Caddy** | ✅ Läuft | Docker container `caddy`, Port 80/443 |
| **n8n** | ⚠️ Legacy | Container `n8n-lx1z-n8n-1` (ephemeral Port) → V1 ersetzt ihn |
| **Open WebUI** | ⚠️ Unbekannt | DNS `openwebui.apexcore.group` → Port 3000 |
| **Hermes** | ⚠️ Ephemeral Port | DNS `hermes.apexcore.group` → Port 32772 (nicht stabil!) |
| **Paperclip** | ⚠️ Ephemeral Port | DNS `paperclip.apexcore.group` → Port 52309 (nicht stabil!) |
| **OpenClaw** | ⚠️ Unbekannt | `/opt/openclaw/` auf VPS, Port 45261 |
| **Ollama** | ❓ Unbekannt | Nicht in Caddyfile gefunden |
| **cmd-api** | ✅ Läuft | Python-Prozess Port 7070 |
| **Heartbeat-Gateway** | ✅ Läuft | Port 18789 (OpenRouter-Proxy) |
| **Notion Backup** | ✅ Aktiv | Cron 02:30 täglich, `/root/scripts/notion-backup.sh` |

---

## Gefundene Ports (aus Caddyfile + deploy.yml)

```
80, 443      caddy (Docker)
3000         open-webui
4000         hermes-agent (V1, neu)
5678         n8n
7070         cmd-api (Python)
8000         openclaw
8080         open-webui intern / hermes-webui intern
11434        ollama
18789        heartbeat-gateway / OpenRouter-Proxy
32772        hermes (EPHEMERAL — instabil!)
45261        openclaw
52309        paperclip (EPHEMERAL — instabil!)
```

---

## Bestehende Datei-Pfade auf dem VPS

```
/opt/openclaw/reverse-proxy/Caddyfile   ← aktuell aktive Caddy-Config (wird migriert)
/opt/apexcore-dashboard/index.html      ← Dashboard
/opt/apexcore/cmd-api/server.py         ← cmd-api
/root/scripts/notion-backup.sh          ← Notion-Backup-Cron
```

## Ziel-Pfade V1

```
/srv/apexcore/
  infra-compose/      docker-compose.yml, Caddyfile, .env
  ai-stack/           docker-compose.yml, hermes-config.yaml, .env
  automation-stack/   docker-compose.yml, .env, templates/
  cmd-api/            server.py
  dashboard/          index.html
  docs/               *.md
  scripts/            *.sh
  backups/            (Caddy-Config-Backups etc.)
```

---

## Volumes (bekannt / inferred)

| Volume | Service | Inhalt |
|---|---|---|
| `caddy_data` | Caddy | TLS-Zertifikate (acme) |
| `caddy_config` | Caddy | Config-Cache |
| `n8n_data` | n8n | Workflows, Credentials |
| `open_webui_data` | Open WebUI | Users, Settings, Chat-History |
| `ollama_data` | Ollama | Heruntergeladene Modelle |

**Kritisch:** `n8n_data` muss beim Container-Replace erhalten bleiben. Volume überlebt `docker compose down`.

---

## Erkannte Risiken

| Risiko | Priorität | Maßnahme |
|---|---|---|
| Hermes/Paperclip auf Ephemeral Ports | 🔴 Hoch | Feste Ports in V1 compose |
| cmd-api: `shell=True`, kein GET /health | 🟡 Mittel | V2 server.py bereinigt |
| Caddyfile nutzt `172.17.0.1` statt Container-Namen | 🟡 Mittel | V1 Caddyfile migiert auf Container-Namen |
| Kein `.env` im Repo | ✅ OK | `.env.example` angelegt; `.env` manuell auf VPS |
| Kein `.gitignore` | ✅ Behoben | `.gitignore` angelegt |
| OpenClaw-Image unbekannt | 🟡 Mittel | Placeholder in compose; manuell ausfüllen |

---

## Was in V1 NICHT angefasst wird

- Heartbeat-Gateway (Port 18789) — läuft stabil, wird nicht verändert
- Notion-Backup-Cron (`/root/scripts/notion-backup.sh`) — bleibt unverändert
- DNS-Einträge — Porkbun-Setup im deploy.yml bereits vorhanden
