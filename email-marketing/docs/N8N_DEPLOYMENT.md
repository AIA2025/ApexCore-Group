# n8n Deployment & Secrets (Task 4–6)

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

# Abandoned Cart Templates (noch nicht angelegt — es gibt noch keine
# Cart-Reminder/Discount-Copy in docs/WELCOME_SEQUENCES.md)
BREVO_TPL_CART_REMINDER=
BREVO_TPL_CART_DISCOUNT=
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

**n8n UI → Credentials → New → Header Auth**

| Feld   | Wert                          |
|--------|--------------------------------|
| Name   | `Brevo API Key`                |
| Header | `api-key`                       |
| Value  | (Wert aus `BREVO_API_KEY` einfügen) |

Diese Credential wird von beiden importierten Workflows
(`optin-to-brevo`, `abandoned-cart-followup`) für alle Brevo-HTTP-Request-
Nodes genutzt.

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

## Checkliste

- [ ] `/root/.apexcore.env` um Brevo-ENV-Vars ergänzt
- [ ] docker-compose n8n-Service: `env_file`, `NODE_FUNCTION_ALLOW_BUILTIN`, Volume für `n8n_log.json`
- [ ] Credential "Brevo API Key" (Header Auth) in n8n angelegt
- [ ] Beide Workflows importiert, Credentials verknüpft, IDs geprüft, aktiviert
- [ ] Webhook-URLs getestet (curl-Beispiele oben)
