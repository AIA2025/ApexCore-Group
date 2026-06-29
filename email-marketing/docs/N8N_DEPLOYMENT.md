# n8n Deployment & Secrets (Task 4–6)

## 0. Tatsächliches Deployment: n8n Cloud (Stand 29.06.2026)

Die ursprüngliche Annahme in diesem Dokument (selbst-gehostetes n8n auf
einem VPS, Import per REST-API/Skript, Logging in eine Host-Datei) trifft
auf das tatsächlich genutzte Konto **nicht** zu: ApexCore betreibt
**n8n Cloud** (`https://apexcoregroup.app.n8n.cloud`). Dort gibt es keinen
Host-Dateisystem-Zugriff und keine klassische REST-API-Anmeldung — die
Workflows wurden stattdessen direkt über den offiziellen n8n-MCP-Server
(Workflow-SDK) im Cloud-Workspace angelegt und aktiviert. Abschnitte 1–7
unten beschreiben weiterhin die Logik/ENV-Variablen korrekt, aber Schritte
2 ("Docker Compose"), 4 ("Workflows importieren" per Skript) und 6
("Logging" in `/root/n8n_log.json`) gelten **nicht** für die Cloud-Instanz.

**Live-Status:**

| Workflow | Workflow-ID | Status |
|---|---|---|
| ApexCore - Opt-in to Brevo | `jeF09hmOYJr9iBAY` | aktiv |
| ApexCore - Welcome Sequence Followup (Mail 2-4) | `1QOyZQ9gJ9RWk6SY` | aktiv |
| ApexCore - Abandoned Cart Follow-up | `pjGSyElFgIXQXGT3` | aktiv |

**Webhook-Basis-URL (Cloud statt eigener Domain):**
`https://apexcoregroup.app.n8n.cloud/webhook/...` (siehe Abschnitt 5 für
die vollständigen Pfade — `n8n.apexcore.group` dort existiert nicht und
muss durch die Cloud-URL ersetzt werden).

**Anpassungen gegenüber den JSON-Workflow-Dateien in diesem Repo:**

- Die Logging-Nodes (`Log to /root/n8n_log.json`) nutzen in der Cloud-Version
  **kein** `require('fs')` mehr (n8n Cloud erlaubt keinen Dateisystemzugriff
  im Code-Node-Sandbox). Sie formen stattdessen nur den Log-Eintrag als JSON
  und geben ihn zurück — nachvollziehbar über den **Executions-Tab** der
  jeweiligen Cloud-Workflows statt über eine Host-Datei.
- `Trigger Welcome Sequence (Mail 2-4)` ruft `$env.N8N_BASE_URL` mit Fallback
  auf `https://apexcoregroup.app.n8n.cloud` auf (statt `http://localhost:5678`).

**Einziger verbleibender manueller Schritt:** Der n8n-MCP-Server stellt
**keinen** Tool zum Anlegen von Credentials bereit (nur `list_credentials`
zum Lesen). Die Credential "Brevo API Key" muss daher einmalig manuell im
n8n-Cloud-Dashboard angelegt werden (siehe Abschnitt 3) — alle drei
Workflows referenzieren sie bereits per Platzhalter und müssen nach dem
Anlegen nur noch zugeordnet werden (n8n zeigt das an den jeweiligen
HTTP-Request-Nodes als "Credential fehlt" an).

## 1. ENV-Variablen

In `/root/.apexcore.env` (gleiche Datei, die `deploy-all.sh` bereits nutzt)
ergänzen:

```bash
# Brevo
BREVO_API_KEY=xkeysib-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Brevo List IDs (bereits live angelegt am 29-06-2026, siehe
# docs/BREVO_LISTS_TAGS.md)
BREVO_LIST_DIGITAL_PRODUCTS=4
BREVO_LIST_ECOM_MERCH=5
BREVO_LIST_GENERAL_LEADS=6
BREVO_LIST_VIP=7

# Brevo Template IDs (Mail 1 je Sequenz/Sprache, bereits live angelegt
# am 29-06-2026, siehe docs/WELCOME_SEQUENCES.md)
BREVO_TPL_DIGITAL_DE=1
BREVO_TPL_DIGITAL_EN=2
BREVO_TPL_ECOM_DE=9
BREVO_TPL_ECOM_EN=10
BREVO_TPL_GENERAL_DE=
BREVO_TPL_GENERAL_EN=

# Brevo Template IDs Mail 2-4 (für welcome-sequence-followup.json, alle
# 16 Templates bereits live angelegt am 29-06-2026, siehe docs/WELCOME_SEQUENCES.md)
BREVO_TPL_DIGITAL_M2_DE=3
BREVO_TPL_DIGITAL_M2_EN=4
BREVO_TPL_DIGITAL_M3_DE=5
BREVO_TPL_DIGITAL_M3_EN=6
BREVO_TPL_DIGITAL_M4_DE=7
BREVO_TPL_DIGITAL_M4_EN=8
BREVO_TPL_ECOM_M2_DE=11
BREVO_TPL_ECOM_M2_EN=12
BREVO_TPL_ECOM_M3_DE=13
BREVO_TPL_ECOM_M3_EN=14
BREVO_TPL_ECOM_M4_DE=15
BREVO_TPL_ECOM_M4_EN=16

# Basis-URL der n8n-Instanz selbst (für den internen Aufruf
# optin-to-brevo -> welcome-sequence-followup, siehe Abschnitt 7)
N8N_BASE_URL=http://localhost:5678

# Abandoned Cart Templates (DE/EN, live angelegt am 29-06-2026, siehe
# docs/WELCOME_SEQUENCES.md Abschnitt "Abandoned Cart")
BREVO_TPL_CART_REMINDER_DE=17
BREVO_TPL_CART_REMINDER_EN=18
BREVO_TPL_CART_DISCOUNT_DE=19
BREVO_TPL_CART_DISCOUNT_EN=20
CART_DISCOUNT_CODE=COMEBACK10
```

**Wichtig:** `BREVO_API_KEY` wird **nicht** direkt in n8n-Node-Parametern
referenziert (das würde den Klartext-Key in Execution-Logs/Workflow-JSON
schreiben). Stattdessen wird er ausschließlich als n8n-Credential
hinterlegt (Schritt 3) — Credential-Werte werden von n8n in Logs/Executions
automatisch maskiert.

## 2. Docker Compose

Im `automation-stack` docker-compose (auf dem VPS, nicht in diesem Repo) den
n8n-Service um folgende Punkte ergänzen:

```yaml
services:
  n8n:
    # ... bestehende Konfiguration unverändert ...
    env_file:
      - /root/.apexcore.env
    environment:
      # erlaubt $env.* Referenzen in Code-Nodes (für Listen-/Template-IDs)
      - NODE_FUNCTION_ALLOW_BUILTIN=fs
    volumes:
      # bestehende Volumes ...
      - /root/n8n_log.json:/root/n8n_log.json
```

Danach:

```bash
docker compose up -d n8n
```

`BREVO_API_KEY` landet damit als ENV-Var im Container, wird aber von keinem
Workflow-Node direkt ausgelesen — nur die Credential (Schritt 3) liest ihn,
und n8n maskiert Credential-Felder grundsätzlich in der UI und in
Execution-Daten.

## 3. n8n Credential anlegen

**Status: noch offen — einziger verbleibender manueller Schritt (siehe Abschnitt 0).**

**n8n Cloud UI (`https://apexcoregroup.app.n8n.cloud`) → Credentials → New → Header Auth**

| Feld   | Wert                          |
|--------|--------------------------------|
| Name   | `Brevo API Key`                |
| Header | `api-key`                       |
| Value  | (Wert aus `BREVO_API_KEY` einfügen) |

Diese Credential wird von allen drei importierten Workflows
(`optin-to-brevo`, `welcome-sequence-followup`, `abandoned-cart-followup`)
für alle Brevo-HTTP-Request-Nodes genutzt.

## 4. Workflows importieren

```bash
export N8N_PASSWORD="..."          # n8n-Login-Passwort, nicht der Brevo-Key
export N8N_URL="http://localhost:5678"
bash email-marketing/deploy-email-workflows.sh
```

Das Skript loggt sich in n8n ein, verknüpft die Brevo-Credential (falls
bereits angelegt) und importiert beide Workflows **inaktiv**. Danach in der
n8n-UI:

1. Workflow öffnen, Credential-Zuordnung an allen HTTP-Request-Nodes prüfen
2. ENV-Variablen aus Schritt 1 prüfen (Listen-/Template-IDs müssen gesetzt sein)
3. Workflow aktivieren (Toggle oben rechts)

## 5. Webhook-Endpunkte

| Workflow                  | Methode | Pfad                                    |
|----------------------------|---------|------------------------------------------|
| Opt-in → Brevo             | POST    | `https://n8n.apexcore.group/webhook/optin` |
| Welcome Sequence Followup (Mail 2-4) | POST | `https://n8n.apexcore.group/webhook/welcome-followup` (intern, siehe Abschnitt 7) |
| Abandoned Cart Follow-up   | POST    | `https://n8n.apexcore.group/webhook/cart-abandon` |

### Beispiel-Requests

```bash
curl -X POST https://n8n.apexcore.group/webhook/optin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "kunde@example.com",
    "name": "Max",
    "source": "gumroad",
    "product_type": "digital",
    "language": "DE"
  }'

curl -X POST https://n8n.apexcore.group/webhook/cart-abandon \
  -H "Content-Type: application/json" \
  -d '{
    "email": "kunde@example.com",
    "product_name": "ApexCore Hoodie",
    "cart_url": "https://shop.apexcore.group/cart/abc123"
  }'
```

## 6. Logging

Beide Workflows schreiben einen JSON-Log-Eintrag pro Lauf nach Host-Pfad
`/root/n8n_log.json` (eine Zeile pro Eintrag, JSON Lines). Der `BREVO_API_KEY`
erscheint dort nicht, da der Log-Node ausschließlich nicht-sensitive Felder
(E-Mail, Source, Liste, Timestamp) schreibt.

## 7. Mail 2-4 als n8n-Workflow statt Brevo-Automation

`docs/WELCOME_SEQUENCES.md` ging ursprünglich davon aus, dass die Delay-
Sequenzen für Mail 2-4 als **Brevo Automation** (UI-only, keine
Creation-API vorhanden) verdrahtet werden. Live-Check der Brevo-API
(`GET /v3/automation/*`, `/v3/automations`, `/v3/marketing-automation/*`)
bestätigt: es gibt auf diesem Plan **keinen** Endpoint, um Automations
programmatisch anzulegen — das bleibt tatsächlich UI-only.

**Lösung:** Mail 2-4 laufen stattdessen komplett innerhalb von n8n, ohne
jeden manuellen Brevo-UI-Schritt:

- `optin-to-brevo.json` ruft nach dem Versand von Mail 1 zusätzlich (parallel
  zum Logging, nicht blockierend für die Webhook-Antwort) den eigenen
  n8n-Endpoint `POST /webhook/welcome-followup` auf (`N8N_BASE_URL` aus
  Schritt 1).
- `welcome-sequence-followup.json` empfängt das, antwortet sofort
  (`status: queued`) und läuft im Hintergrund mit `Wait`-Nodes weiter:
  - `digital-products`: Wait 2 Tage → Mail 2 → Wait 2 Tage → Mail 3 → Wait 3 Tage → Mail 4
  - `ecom-merch`: Wait 2 Tage → Mail 2 → Wait 3 Tage → Mail 3 → Wait 3 Tage → Mail 4
  - `general-leads`/`vip` (keine Sequenz vorgesehen) → No-Op, kein Mail-Versand.
- Template-IDs pro Stufe kommen aus den neuen `BREVO_TPL_*_M2/M3/M4_*`
  ENV-Vars (Schritt 1) — alle 16 Templates existieren bereits.
- Logging nach `/root/n8n_log.json` identisch zu den anderen beiden
  Workflows.

Damit ist die komplette 4-Mail-Sequenz für beide Listen vollständig
automatisiert und reproduzierbar aus diesem Repo importierbar — ohne
manuellen Brevo-Dashboard-Klick.

## Checkliste (n8n Cloud, tatsächlicher Stand 29.06.2026)

- [x] Brevo-ENV-Vars (Listen-/Template-IDs) live in Brevo angelegt, siehe `docs/BREVO_LISTS_TAGS.md` / `docs/WELCOME_SEQUENCES.md`
- [x] Alle drei Workflows per n8n-MCP-Workflow-SDK im Cloud-Workspace angelegt (`jeF09hmOYJr9iBAY`, `1QOyZQ9gJ9RWk6SY`, `pjGSyElFgIXQXGT3`) und aktiviert
- [ ] Credential "Brevo API Key" (Header Auth) in n8n Cloud angelegt — **manuell, kein API/MCP-Tool verfügbar**
- [ ] Nach Anlegen der Credential: an allen Brevo-HTTP-Request-Nodes in allen drei Workflows zuordnen (n8n markiert sie sonst als "Credential fehlt")
- [ ] Webhook-URLs gegen `https://apexcoregroup.app.n8n.cloud/webhook/...` getestet (curl-Beispiele oben, Domain anpassen)

Die untenstehenden Abschnitte 1–7 (ENV-Variablen-Referenz, Webhook-Pfade,
Sequenz-Logik) bleiben fachlich gültig; Abschnitte 2, 4 und 6 beschreiben
jedoch eine selbst-gehostete VPS-Variante, die für das tatsächlich genutzte
n8n-Cloud-Konto nicht zutrifft (siehe Abschnitt 0).
