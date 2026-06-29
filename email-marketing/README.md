# ApexCore Email-Marketing Infrastructure

Vollständige Email-Marketing-Pipeline für Merch, E-Com & digitale Produkte
auf Basis von Brevo + n8n (`automation-stack`, KVM8 VPS).

## Scope dieses Verzeichnisses

Diese Artefakte sind copy-paste-ready vorbereitet. Die folgenden Schritte
erfordern echten Zugriff auf Brevo-Dashboard, Hostinger cPanel und den
n8n-Host und müssen von einem Operator mit diesen Zugängen ausgeführt
werden — sie können nicht aus diesem Repo heraus automatisiert werden
(Account-Anlage, Domain-Verifizierung, DNS-Einträge, Secrets-Eingabe).

## Inhalt

| Datei | Zweck |
|---|---|
| [`docs/BREVO_SETUP.md`](docs/BREVO_SETUP.md) | Task 1 — Account, Domain-Auth, DKIM/SPF/DMARC, Sender |
| [`docs/BREVO_LISTS_TAGS.md`](docs/BREVO_LISTS_TAGS.md) | Task 2 — Listen, Contact-Attribute ("Tags"), Segmente |
| [`docs/WELCOME_SEQUENCES.md`](docs/WELCOME_SEQUENCES.md) | Task 3 — 4-Mail-Sequenzen DE/EN für beide Listen |
| [`n8n-workflows/optin-to-brevo.json`](n8n-workflows/optin-to-brevo.json) | Task 4 — Opt-in-Webhook → Brevo, triggert Welcome-Sequence-Followup |
| [`n8n-workflows/welcome-sequence-followup.json`](n8n-workflows/welcome-sequence-followup.json) | Task 3/4 — Mail 2-4 Delay-Sequenz (ersetzt Brevo-Automation, die keine Creation-API hat) |
| [`n8n-workflows/abandoned-cart-followup.json`](n8n-workflows/abandoned-cart-followup.json) | Task 5 — Abandoned-Cart-Webhook → Delay → Reminder/Discount |
| [`docs/N8N_DEPLOYMENT.md`](docs/N8N_DEPLOYMENT.md) | Task 6 — ENV-Vars, Docker Compose, Credential-Setup, Webhook-URLs |
| [`deploy-email-workflows.sh`](deploy-email-workflows.sh) | Import-Skript für alle drei Workflows (folgt dem Pattern aus `deploy.sh`) |

## Reihenfolge

1. `docs/BREVO_SETUP.md` — Account + DNS
2. `docs/BREVO_LISTS_TAGS.md` — Listen + Attribute, IDs notieren
3. `docs/WELCOME_SEQUENCES.md` — Templates in Brevo anlegen, Template-IDs notieren
4. `docs/N8N_DEPLOYMENT.md` — ENV-Vars setzen, Credential anlegen, Workflows importieren & aktivieren

## Webhook-Endpunkte (nach Deployment)

```
POST https://n8n.apexcore.group/webhook/optin
POST https://n8n.apexcore.group/webhook/cart-abandon
```
