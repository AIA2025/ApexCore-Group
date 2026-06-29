# Brevo Account & Domain-Authentifizierung (Task 1)

Status: Account, Domain-Anlage und Sender sind bereits live (29-06-2026, via
Brevo API). **Update (29-06-2026, später am Tag):** Live-DNS-Check zeigt,
dass die `brevo-code`-TXT- und die `_dmarc`-TXT-Records bei Porkbun
inzwischen bereits eingetragen wurden — Brevo erkennt beide bereits als
`status: true`. DKIM (2× CNAME) fehlt noch komplett, SPF existiert zwar
(`v=spf1 include:_spf.mail.hostinger.com ~all`), enthält aber noch nicht
`include:spf.brevo.com`. Ein Aufruf von `PUT
/v3/senders/domains/apexcore.group/authenticate` schlägt deshalb aktuell
noch fehl:

```
{"code":"bad_request","message":"The domain cannot be authenticated. Check
your domain DNS panel and ensure Brevo code, DKIM record and DMARC record
are added correctly."}
```

(Hinweis: einen separaten `/verify`-Endpoint gibt es in der API nicht —
`verified` scheint nur über das Dashboard oder zusammen mit `authenticate`
gesetzt zu werden.) Sobald die beiden DKIM-CNAMEs unten bei Porkbun
eingetragen sind, kann `authenticate` per API erneut versucht werden, ohne
dass jemand ins Dashboard muss.

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

## 2. Domain — angelegt, Brevo-Code TXT bereits live

Domain `apexcore.group` wurde via `POST /v3/senders/domains` angelegt
(domain id `6a424bb1a2567b6c0e0d86b2`). Der Verification-Record ist
**bereits bei Porkbun eingetragen und von Brevo bestätigt** (`brevo_code.status: true`,
live per DNS-Lookup verifiziert):

```
Type:  TXT
Host:  apexcore.group  (oder "@")
Value: brevo-code:40c34601a468dbf26ca00e2d47805dbc   ✅ live
```

## 3. DKIM — noch offen, einzige verbleibende DNS-Lücke

Brevo nutzt hier CNAME- statt klassische TXT-Records. **Live-DNS-Check
zeigt: diese beiden Records existieren noch nicht** — das ist aktuell der
einzige Blocker für `authenticate`:

```
Type:  CNAME
Host:  brevo1._domainkey
Value: b1.apexcore-group.dkim.brevo.com   ❌ fehlt noch

Type:  CNAME
Host:  brevo2._domainkey
Value: b2.apexcore-group.dkim.brevo.com   ❌ fehlt noch
```

Bei Porkbun eintragen. Danach kann **per API** erneut probiert werden:

```bash
curl -X PUT -H "api-key: $BREVO_API_KEY" \
  "https://api.brevo.com/v3/senders/domains/apexcore.group/authenticate"
```

(kein Dashboard-Klick nötig, sofern die API das DNS dann als korrekt erkennt).

## 4. SPF einrichten — Record existiert, Brevo-Include fehlt

Brevo hat bei `POST /v3/senders` (Sender "ApexCore") `"spfError": true`
zurückgegeben. **Live-DNS-Check zeigt:** es existiert bereits ein
SPF-Record für Hostinger, aber ohne Brevo:

```
v=spf1 include:_spf.mail.hostinger.com ~all     ⚠️ aktuell live, ohne Brevo
```

**Nicht** einen zweiten SPF-TXT-Record anlegen (pro Domain ist nur einer
gültig) — stattdessen den bestehenden Record bei Porkbun bearbeiten und
`include:spf.brevo.com` ergänzen:

```
v=spf1 include:spf.brevo.com include:_spf.mail.hostinger.com ~all
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
- [x] TXT `brevo-code` bei Porkbun eingetragen — von Brevo bestätigt
- [x] TXT `_dmarc` bei Porkbun eingetragen — von Brevo bestätigt (abweichender, aber gültiger `rua`-Wert)
- [ ] 2× CNAME DKIM (`brevo1._domainkey`, `brevo2._domainkey`) bei Porkbun eintragen — **einzige verbleibende DNS-Lücke**
- [ ] Bestehenden SPF-Record bei Porkbun um `include:spf.brevo.com` ergänzen
- [ ] Danach `PUT /v3/senders/domains/apexcore.group/authenticate` per API (oder Dashboard) erneut ausführen
- [x] Sender "ApexCore" `<noreply@apexcore.group>` angelegt (API) — wird erst nach erfolgreicher Domain-Authentifizierung `active`
- [ ] Reply-to + Default-Transactional-Sender manuell im Dashboard setzen
