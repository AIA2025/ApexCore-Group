# Runbook: Orchestrierung & Recovery V1

> Paperclip Projekt: `00-Runbooks` / Issue: APE-1
> Stand: 2026-06-01

---

## 1. Stack-Übersicht

| Dienst       | Port  | systemd-Unit    | Beschreibung                       |
|--------------|-------|-----------------|------------------------------------|
| Caddy        | 80/443| docker (caddy)  | Reverse Proxy, TLS                 |
| Paperclip    | 3100  | paperclip       | Control Plane, UI, API             |
| Hermes       | 7071  | hermes          | Dispatch-Execution-Layer           |
| cmd-api      | 7070  | (python/nohup)  | Command-API für externe Trigger    |

---

## 2. Dienste starten / stoppen / neu starten

```bash
# Paperclip
systemctl start|stop|restart paperclip
journalctl -u paperclip -f

# Hermes
systemctl start|stop|restart hermes
journalctl -u hermes -f

# Caddy (Docker)
docker restart caddy
docker logs caddy --tail 50 -f
```

---

## 3. Health Checks

```bash
# Paperclip
curl -s http://127.0.0.1:3100/api/health | python3 -m json.tool

# Hermes
curl -s http://127.0.0.1:7071/health | python3 -m json.tool

# cmd-api
curl -s http://127.0.0.1:7070/health
```

---

## 4. Paperclip neu starten (Daten erhalten)

```bash
systemctl restart paperclip
# Daten liegen in /opt/paperclip/data — bleiben erhalten
```

---

## 5. Vollständiges Re-Seeding (Daten verloren / frische Instanz)

```bash
export DISPATCHER_TOKEN="<token>"
bash /opt/apexcore/paperclip/seed.sh
```

Das Script legt Company, Agent, alle 7 Projekte und die 7 Issue-Stubs neu an.

---

## 6. DISPATCHER_TOKEN rotieren

1. Neuen Token generieren: `openssl rand -hex 32`
2. In `/etc/environment` aktualisieren: `DISPATCHER_TOKEN=<new>`
3. In Paperclip Company-Secrets aktualisieren.
4. Hermes neu starten: `systemctl restart hermes`
5. Adapter-Health-Probe auslösen (Paperclip UI → Agent → Test).

---

## 7. Neuen Agenten in Paperclip registrieren

```bash
curl -X POST http://127.0.0.1:3100/api/companies/<COMPANY_ID>/agents \
  -H "Content-Type: application/json" \
  -d @paperclip/agent-registration.json
```

Vorlagen für alle Agenten (Hermes, Claude Code, Perplexity) in
`paperclip/agent-registration.json`.

---

## 8. Logs & Monitoring

```bash
# Alle ApexCore-Logs
journalctl -u paperclip -u hermes --since "1 hour ago"

# Live-Tail
journalctl -u hermes -f

# Caddy-Requests
docker logs caddy -f
```

---

## 9. Backup & Restore

```bash
# Backup
tar czf /root/backups/paperclip-data-$(date +%Y%m%d_%H%M%S).tar.gz \
  /opt/paperclip/data

# Restore
systemctl stop paperclip
tar xzf /root/backups/paperclip-data-<timestamp>.tar.gz -C /
systemctl start paperclip
```

---

## 10. Deployment (CI/CD)

Änderungen werden per GitHub Actions automatisch deployt:
- Push auf `main` oder `claude/**` → SSH-Deploy auf VPS 76.13.138.73
- Caddy-Config, Dashboard, Hermes-Service werden aktualisiert
- Workflow: `.github/workflows/deploy.yml`
