# ApexCore / Creator OS

Multi-AI platform for work, automation, and business operations.
Running on Hostinger KVM8 VPS (Ubuntu 22.04) via Docker Compose + Caddy.

## Services

| URL | Service | Role |
|---|---|---|
| [ai.apexcore.group](https://ai.apexcore.group) | Open WebUI | Primary chat frontend |
| [hermes.apexcore.group](https://hermes.apexcore.group) | Hermes WebUI | Agent control panel |
| [n8n.apexcore.group](https://n8n.apexcore.group) | n8n | Workflow automation |
| [ops.apexcore.group](https://ops.apexcore.group) | OpenClaw | Ops/Messenger agent |
| [dashboard.apexcore.group](https://dashboard.apexcore.group) | Dashboard | Status overview |

## Quick Start (on VPS)

```bash
# First time
cp /srv/apexcore/ai-stack/.env.example /srv/apexcore/ai-stack/.env
cp /srv/apexcore/automation-stack/.env.example /srv/apexcore/automation-stack/.env
cp /srv/apexcore/infra-compose/.env.example /srv/apexcore/infra-compose/.env
# Edit .env files with real credentials

# Start everything
/srv/apexcore/scripts/stack-start.sh

# Check health
/srv/apexcore/scripts/healthcheck.sh
```

## Documentation

- [`docs/APEXCORE_STACK_STATUS.md`](docs/APEXCORE_STACK_STATUS.md) — Current state & findings
- [`docs/APEXCORE_ORCHESTRATION_V1.md`](docs/APEXCORE_ORCHESTRATION_V1.md) — Architecture
- [`docs/RUNBOOK_ORCHESTRATION_V1.md`](docs/RUNBOOK_ORCHESTRATION_V1.md) — Operations guide
- [`docs/HERMES_ROLE_PROFILE.md`](docs/HERMES_ROLE_PROFILE.md) — Hermes agent definition
- [`docs/NOTION_INTEGRATION_PLAN.md`](docs/NOTION_INTEGRATION_PLAN.md) — Notion setup
- [`docs/README_CADDY.md`](docs/README_CADDY.md) — Caddy / reverse proxy guide

## Stack Layout

```
/srv/apexcore/
  infra-compose/   Caddy reverse proxy
  ai-stack/        Open WebUI, Hermes Agent, Hermes WebUI, Ollama, OpenClaw
  automation-stack/ n8n, Paperclip (V2)
  scripts/         stack-start.sh, stack-stop.sh, healthcheck.sh
  docs/            Architecture docs, runbooks
```
