# Brevo Account & Domain-Authentifizierung (Task 1)

Diese Schritte erfordern Zugriff auf das Brevo-Dashboard und das Hostinger
cPanel und müssen manuell (oder von einem Operator mit den entsprechenden
Zugängen) ausgeführt werden — es gibt keine API, um ein Brevo-Konto oder
DNS-Einträge ohne menschliche Bestätigung anzulegen.

## 1. Account anlegen

1. https://app.brevo.com/account/register
2. Login-Email: `marketing@apexcore.group`
3. Firmenname: `ApexCore`
4. Nach Bestätigung: **Settings → Senders, Domains & Dedicated IPs**

## 2. Domain verifizieren

1. **Domains → Add a domain** → `apexcore.group`
2. Brevo zeigt einen TXT-Record zur Domain-Verifizierung an, z. B.:
   ```
   Type:  TXT
   Host:  apexcore.group
   Value: brevo-code:xxxxxxxxxxxxxxxxxxxx
   ```
3. Diesen Record in Hostinger cPanel → **Zone Editor → apexcore.group → Add Record** eintragen.
4. Zurück in Brevo auf **Verify** klicken.

## 3. DKIM einrichten

Nach der Domain-Verifizierung zeigt Brevo zwei DKIM-Records (Brevo generiert
diese individuell pro Account — die folgenden sind das erwartete Format,
nicht die echten Werte):

```
Type:  TXT
Host:  mail._domainkey.apexcore.group
Value: k=rsa; p=<von Brevo generierter Public Key>
```

In Hostinger cPanel Zone Editor eintragen, dann in Brevo auf **Authenticate**
klicken, um DKIM zu validieren.

## 4. SPF einrichten

Falls noch kein SPF-Record existiert, neuen TXT-Record anlegen:

```
Type:  TXT
Host:  apexcore.group
Value: v=spf1 include:spf.brevo.com mx ~all
```

Falls bereits ein SPF-Record existiert (z. B. von Hostinger Mail oder einem
anderen Versanddienst), **nicht** einen zweiten anlegen — stattdessen
`include:spf.brevo.com` in den bestehenden Record einfügen, da pro Domain nur
ein SPF-TXT-Record gültig ist:

```
v=spf1 include:spf.brevo.com include:<bestehender-anbieter> mx ~all
```

## 5. DMARC einrichten

Neuen TXT-Record anlegen (verschärft schrittweise, beginnend mit `p=none`
zur Beobachtung, danach auf `quarantine`/`reject` hochstufen):

```
Type:  TXT
Host:  _dmarc.apexcore.group
Value: v=DMARC1; p=none; rua=mailto:dmarc-reports@apexcore.group; fo=1
```

Nach 2–4 Wochen ohne Fehlalarme auf `p=quarantine`, danach `p=reject`
hochstufen.

## 6. Sender-Name setzen

**Senders, Domains & Dedicated IPs → Senders → Add a sender**

| Feld          | Wert                       |
|---------------|----------------------------|
| Sender name   | `ApexCore`                 |
| Sender email  | `noreply@apexcore.group`   |
| Reply-to      | `sales@apexcore.group`     |

Für transaktionale/Welcome-Mails diesen Sender als Default in
**Transactional → Settings** hinterlegen.

## Checkliste

- [ ] Brevo-Account mit `marketing@apexcore.group` erstellt
- [ ] Domain `apexcore.group` verifiziert (TXT)
- [ ] DKIM-Record eingetragen und in Brevo als "Authenticated" markiert
- [ ] SPF-Record enthält `include:spf.brevo.com`
- [ ] DMARC-Record unter `_dmarc.apexcore.group` aktiv
- [ ] Sender "ApexCore" `<noreply@apexcore.group>` angelegt
