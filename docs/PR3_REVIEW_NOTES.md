# PR #3 Review Notes — Hard Technical Assessment

_Reviewer: Claude Code | Datum: 2026-05-28 | Branch: claude/gracious-brahmagupta-mqZly_

---

## Bewertung

PR #3 liefert eine solide Grundstruktur, hat aber **7 technische Bugs** (davon 3 kritisch, die bei `docker compose up` sofort scheitern) sowie fehlende Architektur-Tiefe für Paperclip.

---

## Gefundene Bugs — Priorisiert

### 🔴 KRITISCH — blockiert Runtime

**1. Cross-Netz-Bug: n8n kann Hermes und OpenClaw nicht erreichen**

n8n ist nur in `automation_net`. `hermes-agent` und `openclaw` sind in `ai_net`.
Docker-DNS löst Container-Namen nicht netzwerkübergreifend auf.

```yaml
# automation-stack: n8n env hat
HERMES_API_URL=http://hermes-agent:4000/v1   # ← NXDOMAIN aus automation_net
OPENCLAW_API_URL=http://openclaw:8000         # ← NXDOMAIN aus automation_net
```

Folge: n8n-Workflows, die Hermes oder OpenClaw aufrufen, schlagen mit Connection Error fehl.

Fix: n8n in beide Netze (`automation_net` + `ai_net`). Implementiert in diesem PR.

---

**2. OpenClaw: Image existiert nicht**

```yaml
image: ${OPENCLAW_IMAGE:-ghcr.io/aia2025/openclaw:latest}
```

`ghcr.io/aia2025/openclaw:latest` existiert nicht. `docker compose up` für ai-stack scheitert beim Pull mit `manifest unknown`.

Fix: OpenClaw auf Compose-Profile `ops` verschoben. Stack startet ohne es. Manuell aktivieren sobald Image vorliegt.

---

**3. deploy.yml scp-action source: falsches YAML-Format**

```yaml
source: >           # ← YAML folded scalar: kollabiert Newlines zu Spaces
  infra-compose/docker-compose.yml,
  infra-compose/Caddyfile,
  ...
```

scp-action erwartet newline-getrennte Einträge. Mit `>` bekommt die Action einen einzigen langen String. Folge: Keine Dateien werden transferiert, Deploy ist ein No-Op.

Fix: Umstellung auf tar.gz-Paket + einzelne SCP-Datei. Implementiert in diesem PR.

---

### 🟡 MITTEL — funktioniert nicht korrekt

**4. deploy.yml DNS-Step läuft nie**

```yaml
- name: Add DNS Records
  if: ${{ env.PB_KEY != '' }}   # ← env.PB_KEY ist step-level, nicht job-level
  env:
    PB_KEY: ${{ secrets.PORKBUN_APIKEY }}   # ← wird erst beim Step gesetzt
```

GitHub Actions evaluiert `if`-Bedingungen VOR dem Step. `env.PB_KEY` ist leer weil es nicht im job-level `env:` Block steht. DNS-Schritt läuft nie.

Fix: Kondition entfernt, Prüfung im Skript selbst. Implementiert.

---

**5. Caddy Healthcheck schlägt fehl**

```yaml
test: ["CMD", "wget", "-qO-", "http://localhost:80"]
```

Caddy gibt auf Port 80 ohne gültigen Host-Header kein 200 zurück — normalerweise Redirect auf HTTPS oder 404. Caddy container wird nie `healthy`.

Fix: `["CMD-SHELL", "nc -z 127.0.0.1 80"]` — prüft nur ob TCP-Port offen ist.

---

**6. Open WebUI Healthcheck — curl nicht garantiert verfügbar**

Open WebUI läuft auf einem Python-basierten Image. `curl` ist nicht garantiert installiert. Healthcheck kann fehlschlagen.

Fix: Auf `wget` umgestellt (busybox häufiger verfügbar) mit Python-Fallback. `start_period: 60s` gesetzt.

---

**7. Paperclip Caddyfile Kommentar falscher Port**

```caddy
paperclip.apexcore.group {
    # reverse_proxy paperclip:3000  ← falsch: Container-Port ist 80 (mapping: 3002:80)
```

Wenn Paperclip aktiviert wird und jemand den Kommentar entkommentiert, broken routing.

Fix: Port im Kommentar auf `80` korrigiert.

---

## Was gut ist

| Aspekt | Bewertung |
|---|---|
| Stack-Trennung (3 Compose-Files) | ✅ Sauber |
| Port-Binding `127.0.0.1` only | ✅ Korrekt |
| Volume-Namen | ✅ Konsistent |
| Netzwerk-Isolation Konzept | ✅ Gut gedacht |
| Paperclip auf Compose-Profile | ✅ Richtig |
| Start-Reihenfolge in scripts/ | ✅ Korrekt |
| .env.example für alle Stacks | ✅ Vorhanden |
| Legacy-Backups in docs/legacy/ | ✅ Sauber |
| n8n Port-Bindung intern | ✅ Korrekt |

---

## Was vor Merge zwingend gefixt werden muss

- [x] n8n cross-network Bug
- [x] openclaw image fehlt / Stack-Crash
- [x] deploy.yml scp-action Format
- [x] deploy.yml DNS-Condition
- [x] Caddy Healthcheck
- [x] Caddyfile Paperclip Port-Kommentar
- [x] PAPERCLIP_CONTROL_PLANE_V2.md fehlt
- [x] APEXCORE_ORG_MODEL.md fehlt

Alle Punkte wurden in diesem Review-Commit behoben.

---

## Bewusst für V2 gelassen

| Punkt | Begründung |
|---|---|
| LiteLLM / n8n Version nicht gepinnt | `:latest` akzeptabel für V1-Betrieb; V2 braucht explizites Version-Pinning |
| OpenClaw Image nicht real | Kein öffentliches Image bekannt; Placeholder + Profil-Schutz ausreichend |
| Memory-Layer für Hermes | V2-Feature; LiteLLM V1 ist bewusster Kompromiss |
| Paperclip nicht aktiviert | Korrekt — V1-Basis muss stabil sein, bevor Control-Plane drüber kommt |
| `.github/secrets/vps_deploy_key` im Repo | War bewusster Commit ("Store VPS deploy SSH key") — sollte geprüft werden ob Public Key oder encrypted; in .gitignore aufnehmen falls sensitiv |
| Notion Backup Script `/root/scripts/notion-backup.sh` | Liegt auf VPS, nicht im Repo — sollte in V2 in `scripts/` aufgenommen werden |

---

## Merge-Empfehlung

**Nach diesem Review-Commit: mergebar.**

Alle kritischen Bugs wurden behoben. Die Architektur ist solide für V1. Paperclip ist als vollständige Control-Plane-Zielarchitektur dokumentiert. Die V2-Vorbereitungen sind im Repo verankert.
