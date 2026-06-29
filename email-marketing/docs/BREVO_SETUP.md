# Brevo Account & Domain-Authentifizierung (Task 1)

Status: Account, Domain-Anlage und Sender sind bereits live (29-06-2026, via
Brevo API). Offen ist nur noch das **Eintragen der unten stehenden Records
beim tatsächlichen DNS-Provider** und der Klick auf "Authenticate"/"Verify"
im Brevo-Dashboard — das erfordert DNS-Zugriff und kann nicht über die API
erledigt werden.

## ⚠️ Wichtig: DNS-Provider ist Porkbun, nicht Hostinger

Brevo hat bei der Domain-Anlage automatisch erkannt:
`"domain_provider": "Porkbun"`. Das bedeutet: die **autoritativen
Nameserver für `apexcore.group` zeigen aktuell auf Porkbun**, nicht auf
Hostinger. Die Records unten müssen daher im **Porkbun DNS-Management**
eingetragen werden:

- https://porkbun.com/account/login → Domain Management → `apexcore.group` → DNS Records

Falls die Domain eigentlich über Hostinger cPanel verwaltet werden soll,
zuerst prüfen, ob die Nameserver-Delegation umgestellt werden muss — sonst
landen Einträge im Hostinger cPanel ins Leere, weil die Nameserver dort
nicht autoritativ sind.

## 1. Account — erledigt

- Account: `marketing@apexcore.group`, Firma "ApexCore Group d.o.o."
- Bestätigt via `GET /v3/account`

## 2. Domain — angelegt, Verifizierung offen

Domain `apexcore.group` wurde via `POST /v3/senders/domains` angelegt
(domain id `6a424bb1a2567b6c0e0d86b2`). Brevo gibt folgende **echten**
Records zurück, die jetzt bei Porkbun eingetragen werden müssen:

```
Type:  TXT
Host:  apexcore.group  (oder "@")
Value: brevo-code:40c34601a468dbf26ca00e2d47805dbc
```

Danach in Brevo: **Senders, Domains & Dedicated IPs → Domains → apexcore.group → Verify**.

## 3. DKIM — Records bekannt, noch einzutragen

Brevo nutzt hier CNAME- statt klassische TXT-Records:

```
Type:  CNAME
Host:  brevo1._domainkey
Value: b1.apexcore-group.dkim.brevo.com

Type:  CNAME
Host:  brevo2._domainkey
Value: b2.apexcore-group.dkim.brevo.com
```

Bei Porkbun eintragen, danach in Brevo auf **Authenticate** klicken.

## 4. SPF einrichten

Brevo hat bei `POST /v3/senders` (Sender "ApexCore") `"spfError": true`
zurückgegeben — SPF ist noch nicht gesetzt. Die API hat dafür keinen
fertigen Record zurückgegeben (Brevo zeigt den empfohlenen SPF-String
dashboard-seitig unter Domains → apexcore.group an); Standard-Empfehlung:

```
Type:  TXT
Host:  apexcore.group  (oder "@")
Value: v=spf1 include:spf.brevo.com mx ~all
```

Falls bereits ein SPF-Record existiert, **nicht** einen zweiten anlegen,
sondern `include:spf.brevo.com` in den bestehenden Record einfügen (pro
Domain ist nur ein SPF-TXT-Record gültig):

```
v=spf1 include:spf.brevo.com include:<bestehender-anbieter> mx ~all
```

## 5. DMARC — Record bekannt, noch einzutragen

Von Brevo zurückgegeben (Status bereits `true`, d. h. Brevo erkennt den
Record als ausreichend, sobald er existiert):

```
Type:  TXT
Host:  _dmarc
Value: v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com
```

Hinweis: Brevo schlägt hier standardmäßig `rua=mailto:rua@dmarc.brevo.com`
vor (Brevo sammelt die Reports). Wer eigene Reports unter
`dmarc-reports@apexcore.group` sammeln möchte, kann den `rua`-Wert anpassen
oder per Komma ergänzen: `rua=mailto:rua@dmarc.brevo.com,mailto:dmarc-reports@apexcore.group`.
Nach 2–4 Wochen ohne Fehlalarme von `p=none` auf `p=quarantine`, danach
`p=reject` hochstufen.

## 6. Sender — erledigt

Via `POST /v3/senders` angelegt (sender id `2`):

| Feld          | Wert                       |
|---------------|----------------------------|
| Sender name   | `ApexCore`                 |
| Sender email  | `noreply@apexcore.group`   |

Reply-to (`sales@apexcore.group`) und Default-Sender für
Transactional/Welcome-Mails noch manuell in **Transactional → Settings**
hinterlegen — dafür gibt es keinen API-Endpoint.

## Checkliste

- [x] Brevo-Account mit `marketing@apexcore.group` erstellt
- [x] Domain `apexcore.group` in Brevo angelegt (API)
- [ ] DNS-Records bei **Porkbun** eintragen (TXT brevo-code, 2× CNAME DKIM, TXT SPF, TXT DMARC)
- [ ] In Brevo "Verify" (Domain) und "Authenticate" (DKIM) klicken
- [x] Sender "ApexCore" `<noreply@apexcore.group>` angelegt (API)
- [ ] Reply-to + Default-Transactional-Sender manuell im Dashboard setzen
