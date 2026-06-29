# n8n Deployment & Secrets (Task 4–6)

## 0. Tatsächliches Deployment: n8n Cloud (Stand 29.06.2026)

Die ursprüngliche Annahme in diesem Dokument (selbst-gehostetes n8n auf
einem VPS, Import per REST-API/Skript, Logging in eine Host-Datei) trifft
auf das tatsächlich genutzte Konto **nicht** zu: ApexCore betreibt
**n8n Cloud** (`https://apexcoregroup.app.n8n.cloud`). Dort gibt es keinen
Host-Dateisystem-Zugriff und keine klassische REST-API-Anmeldung — die
Workflows wurden stattdessen direkt über den offiziellen n8n-MCP-Server
(Workflow-SDK) im Cloud-Workspace angelegt und aktiviert. Abschnitte 1–7
unten beschreiben weiterhin die Logik korrekt, aber Schritte 2 ("Docker
Compose"), 4 ("Workflows importieren" per Skript) und 6 ("Logging" in
`/root/n8n_log.json`) gelten **nicht** für die Cloud-Instanz. Abschnitt 1
("ENV-Variablen") beschreibt zudem ein Design, das auf n8n Cloud aus dem
in Abschnitt 0a beschriebenen Grund **nicht** funktioniert — die dort
gelisteten Listen-/Template-IDs sind weiterhin die korrekten, live in
Brevo angelegten Werte, sie werden in den drei Workflows nur direkt als
Literale statt über `$env.*` referenziert.

### 0a. Zweite Plattform-Einschränkung: kein `$env`-Zugriff in Code-/Expression-Nodes

Beim ersten Live-Test des Opt-in-Webhooks (29.06.2026) lieferte
`/webhook/optin` HTTP 200 mit leerem Body statt der erwarteten JSON-Antwort.
Analyse der Execution per `get_execution` (`includeData: true`) zeigte den
tatsächlichen Fehler: `Cannot assign to read only property 'name' of
object 'Error: access to env vars denied'`, ausgelöst in
`workflow-data-proxy-env-provider.js` im JS-Task-Runner von n8n Cloud.

**n8n Cloud verweigert grundsätzlich den Zugriff auf `$env` innerhalb von
Code-Nodes und Ausdrücken** (`={{ $env.X }}`) — unabhängig vom
`NODE_FUNCTION_ALLOW_BUILTIN`-Workaround aus Abschnitt 2, der auf der
selbst-gehosteten Variante zutrifft, aber für Cloud nicht gilt. Betroffen
waren dadurch praktisch alle `$env.*`-Referenzen in allen drei Workflows:

- `Map Source -> List/Tags` (Code-Node, `optin-to-brevo`)
- `Trigger Welcome Sequence (Mail 2-4)` (HTTP-Node-URL, `optin-to-brevo`)
- `Resolve Sequence` (Code-Node, `welcome-sequence-followup`)
- `Brevo: Send Reminder Mail` / `Brevo: Send Discount Mail`
  (HTTP-Node-`jsonBody`, `abandoned-cart-followup`)

**Fix (umgesetzt 29.06.2026, live):** alle `$env.*`-Referenzen in den
genannten Nodes durch die bereits bekannten, live in Brevo angelegten
numerischen IDs als Literale ersetzt (per `update_workflow`/
`setNodeParameter` direkt an den drei aktiven Cloud-Workflows, danach
`publish_workflow`) — Workflow-IDs, Webhook-Pfade und Aktivierungsstatus
blieben dabei unverändert. Die JSON-Dateien in
`email-marketing/n8n-workflows/` in diesem Repo wurden entsprechend
angepasst, damit sie den tatsächlichen Live-Stand widerspiegeln.

Damit bleiben auf n8n Cloud insgesamt zwei bestätigte, plattformbedingte
Einschränkungen: (1) keine `$env`-Variablen in Code-/Expression-Nodes
(dieser Abschnitt, gelöst durch Literale) und (2) keine programmatische
Zuordnung von Generic-Auth-Credentials zu `httpRequest`-Nodes per MCP-Tool
(siehe unten, weiterhin nur manuell lösbar).

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
zum Lesen) — die Credential **"Header Auth account"** (Header Auth, Header
`api-key`) wurde daher bereits manuell im n8n-Cloud-Dashboard angelegt
(Credential-ID `ehIlK7HKhfWPJTaK`, Stand 29.06.2026, sichtbar per
`list_credentials`).

Die **Zuordnung** dieser Credential zu den neun Brevo-HTTP-Request-Nodes
ist jedoch ebenfalls **nicht** per MCP-Tool möglich — getestet wurde
`update_workflow` mit `setNodeCredential` sowie `addNode` mit eingebetteter
`credentials`-Angabe sowie `create_workflow_from_code` mit
`newCredential(...)`-Referenz; alle drei Wege liefern für
`n8n-nodes-base.httpRequest` denselben Fehler ("node type ... does not
accept credential ...") für jeden Generic-Auth-Credential-Typ
(`httpHeaderAuth`, `httpBasicAuth`, `httpQueryAuth`, `httpCustomAuth`,
`httpDigestAuth`, `httpBearerAuth`, `oAuth1Api`, `oAuth2Api`) — nur der
fixe `httpSslAuth`-Slot wird überhaupt akzeptiert. Andere Node-Typen mit
einer einzigen, fest verdrahteten Credential (z. B. `openAiApi` am
`n8n-nodes-base.openAi`-Node) funktionieren über denselben Mechanismus
einwandfrei — die Einschränkung betrifft also gezielt Generic-Auth-Slots
an HTTP-Request-Nodes und wirkt wie eine bewusste Schutzmaßnahme des
MCP-Servers gegen das automatisierte Verdrahten beliebiger Credentials an
beliebige HTTP-Ziele. Die Zuordnung an den neun Nodes (siehe Abschnitt 3)
muss daher ebenfalls manuell in der n8n-Cloud-UI erfolgen.

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

## 3. n8n Credential anlegen + zuordnen

**Status: Credential angelegt (29.06.2026) — Zuordnung an den Nodes noch
offen, einziger verbleibender manueller Schritt (siehe Abschnitt 0).**

Bereits angelegt in der n8n Cloud UI (`https://apexcoregroup.app.n8n.cloud`
→ Credentials → New → Header Auth):

| Feld           | Wert                          |
|----------------|--------------------------------|
| Name           | `Header Auth account` (von n8n vorgeschlagener Default-Name) |
| Credential-ID  | `ehIlK7HKhfWPJTaK`             |
| Header         | `api-key`                       |
| Value          | (Brevo API Key, maskiert in n8n) |

**Noch zu erledigen (manuell, n8n Cloud UI):** Diese Credential an den
neun Brevo-HTTP-Request-Nodes zuordnen — geprüft und bestätigt, dass dies
über keinen der 27 MCP-Server-Tools möglich ist (siehe Abschnitt 0 für die
Details der getesteten Wege). In der UI: jeden Node öffnen → Feld
"Credential for Header Auth" → `Header Auth account` auswählen → Workflow
speichern. Betroffene Nodes:

- **ApexCore - Opt-in to Brevo** (`jeF09hmOYJr9iBAY`): "Brevo: Upsert
  Contact", "Brevo: Send Welcome Mail 1"
- **ApexCore - Welcome Sequence Followup (Mail 2-4)** (`1QOyZQ9gJ9RWk6SY`):
  "Brevo: Send Mail 2", "Brevo: Send Mail 3", "Brevo: Send Mail 4"
- **ApexCore - Abandoned Cart Follow-up** (`pjGSyElFgIXQXGT3`): "Brevo:
  Get Contact (1)", "Brevo: Send Reminder Mail", "Brevo: Get Contact (2)",
  "Brevo: Send Discount Mail"

(`Trigger Welcome Sequence (Mail 2-4)` in `optin-to-brevo` braucht **keine**
Brevo-Credential — er ruft nur den eigenen n8n-Webhook auf.)

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
- [x] Credential "Header Auth account" (Header Auth, `ehIlK7HKhfWPJTaK`) in n8n Cloud angelegt — **manuell, kein API/MCP-Tool verfügbar**
- [ ] Credential an den neun Brevo-HTTP-Request-Nodes in allen drei Workflows zuordnen (siehe Abschnitt 3 für die Liste) — **manuell, nachweislich über keinen der 27 MCP-Tools möglich** (getestet: `setNodeCredential`, `addNode` mit Credentials, `create_workflow_from_code`; alle lehnen Generic-Auth-Credentials an `httpRequest`-Nodes kategorisch ab, vermutlich als Schutzmaßnahme gegen automatisiertes Verdrahten beliebiger Credentials an beliebige HTTP-Ziele)
- [x] `$env`-Zugriffsfehler in Code-/Expression-Nodes behoben (siehe Abschnitt 0a) — alle drei Workflows mit Literal-Werten statt `$env.*` aktualisiert und neu published (29.06.2026)
- [x] Webhook `/webhook/optin` nach dem `$env`-Fix erneut getestet (29.06.2026, Execution-ID 11): `Map Source -> List/Tags` läuft jetzt fehlerfrei durch (korrekte `listId`/`templateId` aus den Literalen), Workflow bricht wie erwartet erst am nächsten Node ab — `Brevo: Upsert Contact` mit `"Credentials not found"` (= die offene, manuelle Credential-Zuordnung oben, kein neuer Bug)

Die untenstehenden Abschnitte 1–7 (ENV-Variablen-Referenz, Webhook-Pfade,
Sequenz-Logik) bleiben fachlich gültig; Abschnitte 2, 4 und 6 beschreiben
jedoch eine selbst-gehostete VPS-Variante, die für das tatsächlich genutzte
n8n-Cloud-Konto nicht zutrifft (siehe Abschnitt 0).
