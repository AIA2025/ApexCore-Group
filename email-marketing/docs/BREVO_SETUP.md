# Brevo Account & Domain-Authentifizierung (Task 1)

## ✅ Status: vollständig abgeschlossen (29-06-2026)

Domain `apexcore.group` ist **verifiziert und authentifiziert**
(`verified: true`, `authenticated: true`, alle 4 DNS-Checks `status: true`).
Beide DKIM-CNAMEs und der SPF-Include wurden via Porkbun-API eingetragen,
danach lief `PUT /v3/senders/domains/apexcore.group/authenticate`
erfolgreich durch (`"Domain has been authenticated successfully."`).
Sender `noreply@apexcore.group` ist jetzt `active: true` — alle 20
E-Mail-Templates wurden per API auf diesen Sender umgestellt (vorher
Stand-in `marketing@apexcore.group`).

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

## 2. Domain — angelegt, Brevo-Code TXT live & bestätigt

Domain `apexcore.group` wurde via `POST /v3/senders/domains` angelegt
(domain id `6a424bb1a2567b6c0e0d86b2`). Verification-Record bei Porkbun
eingetragen und von Brevo bestätigt (`brevo_code.status: true`):

```
Type:  TXT
Host:  apexcore.group  (oder "@")
Value: brevo-code:40c34601a468dbf26ca00e2d47805dbc   ✅ live
```

## 3. DKIM — ✅ live, beide CNAMEs eingetragen und bestätigt

Brevo nutzt hier CNAME- statt klassische TXT-Records. Beide Records wurden
via Porkbun-API angelegt und Brevo bestätigt sie (`dkim1Record.status: true`,
`dkim2Record.status: true`):

```
Type:  CNAME
Host:  brevo1._domainkey
Value: b1.apexcore-group.dkim.brevo.com   ✅ live

Type:  CNAME
Host:  brevo2._domainkey
Value: b2.apexcore-group.dkim.brevo.com   ✅ live
```

Authentifizierung danach erfolgreich per API durchgeführt:

```bash
curl -X PUT -H "api-key: $BREVO_API_KEY" \
  "https://api.brevo.com/v3/senders/domains/apexcore.group/authenticate"
# -> {"domain_name":"apexcore.group","message":"Domain has been authenticated successfully."}
```

## 4. SPF — ✅ live, Brevo-Include ergänzt

Der bestehende SPF-Record für Hostinger wurde bei Porkbun bearbeitet (nicht
ein zweiter Record angelegt — pro Domain ist nur einer gültig) und enthält
jetzt zusätzlich `include:spf.brevo.com`:

```
v=spf1 include:spf.brevo.com include:_spf.mail.hostinger.com ~all   ✅ live
```

## 5. DMARC — bereits live (abweichender, aber ausreichender Wert)

**Live-DNS-Check zeigt:** ein `_dmarc`-TXT-Record existiert bereits und
Brevo akzeptiert ihn (`dmarc_record.status: true`):

```
Type:  TXT
Host:  _dmarc
Value: v=DMARC1; p=none; rua=mailto:postmaster@apexcore.group; adkim=s; aspf=s   ✅ live
```

Hinweis: Brevo selbst hätte standardmäßig `rua=mailto:rua@dmarc.brevo.com`
vorgeschlagen (Brevo sammelt dann die Reports); der jetzige Record sendet
Reports stattdessen an `postmaster@apexcore.group` — das ist für Brevo
ausreichend (`status: true`), kann aber bei Bedarf um
`,mailto:rua@dmarc.brevo.com` ergänzt werden, falls Brevo-seitige
Aggregat-Reports gewünscht sind. Nach 2–4 Wochen ohne Fehlalarme von
`p=none` auf `p=quarantine`, danach `p=reject` hochstufen.

## 6. Sender — ✅ erledigt, jetzt aktiv

Via `POST /v3/senders` angelegt (sender id `2`), nach Domain-Authentifizierung
jetzt `active: true`:

| Feld          | Wert                       |
|---------------|----------------------------|
| Sender name   | `ApexCore`                 |
| Sender email  | `noreply@apexcore.group`   |

Alle 20 E-Mail-Templates (16 Welcome-Sequenz + 4 Abandoned-Cart) wurden per
API von `marketing@apexcore.group` (Stand-in-Sender) auf
`noreply@apexcore.group` umgestellt.

Reply-to (`sales@apexcore.group`) und Default-Sender für
Transactional/Welcome-Mails noch manuell in **Transactional → Settings**
hinterlegen — dafür gibt es keinen API-Endpoint.

## Checkliste

- [x] Brevo-Account mit `marketing@apexcore.group` erstellt
- [x] Domain `apexcore.group` in Brevo angelegt (API)
- [x] TXT `brevo-code` bei Porkbun eingetragen — von Brevo bestätigt
- [x] TXT `_dmarc` bei Porkbun eingetragen — von Brevo bestätigt (abweichender, aber gültiger `rua`-Wert)
- [x] 2× CNAME DKIM (`brevo1._domainkey`, `brevo2._domainkey`) bei Porkbun eingetragen (via Porkbun-API) — von Brevo bestätigt
- [x] Bestehenden SPF-Record bei Porkbun um `include:spf.brevo.com` ergänzt (via Porkbun-API)
- [x] `PUT /v3/senders/domains/apexcore.group/authenticate` erfolgreich ausgeführt — Domain `verified: true`, `authenticated: true`
- [x] Sender "ApexCore" `<noreply@apexcore.group>` jetzt `active: true`
- [x] Alle 20 Templates auf `noreply@apexcore.group` umgestellt (API)
- [ ] Reply-to + Default-Transactional-Sender manuell im Dashboard setzen (kein API-Endpoint vorhanden)
