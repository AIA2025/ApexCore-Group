# Welcome-Sequenzen (Task 3)

Anlegen unter **Brevo → Automations → Create a workflow → "When a contact is
added to a list"**. Pro Liste ein Automation-Workflow mit 4 E-Mails und
Delay-Steps (Tag 0 / 2 / 4 / 7 bzw. 0 / 2 / 5 / 8). Jede Mail existiert als
eigenes **Template** (Transactional → Templates) in DE und EN; die Automation
verzweigt per `IF LANGUAGE = DE` auf das passende Template.

## Status: alle 16 Templates live angelegt (29-06-2026, via API)

| Mail | DE Template-ID | EN Template-ID |
|---|---|---|
| `digital-products` Mail 1 | 1 | 2 |
| `digital-products` Mail 2 | 3 | 4 |
| `digital-products` Mail 3 | 5 | 6 |
| `digital-products` Mail 4 | 7 | 8 |
| `ecom-merch` Mail 1 | 9 | 10 |
| `ecom-merch` Mail 2 | 11 | 12 |
| `ecom-merch` Mail 3 | 13 | 14 |
| `ecom-merch` Mail 4 | 15 | 16 |

Mail-1-IDs (`1, 2, 9, 10`) sind bereits in `N8N_DEPLOYMENT.md` als
`BREVO_TPL_DIGITAL_DE/EN` und `BREVO_TPL_ECOM_DE/EN` eingetragen — diese
triggert der n8n-Opt-in-Workflow direkt. Mails 2–4 müssen noch als
**Automation mit Delay-Steps** in Brevo verdrahtet werden (Templates
existieren bereits, nur die Automation-Workflows fehlen noch — Segment-/
Automation-Erstellung ist über die Brevo-API nicht abgedeckt).

**Offen:**
- Aktuell sind alle Templates auf Sender `marketing@apexcore.group`
  gesetzt (einziger aktiver Sender). Sobald `noreply@apexcore.group` nach
  DNS-Authentifizierung aktiv ist (siehe `BREVO_SETUP.md`), Sender in jedem
  Template auf `noreply@apexcore.group` umstellen.
- Platzhalter-Inhalte (Story, Testimonials, Produktnamen) sind noch
  generisch — siehe Hinweise unten.
- `general-leads` und `vip` haben laut Task-Vorgabe keine eigene
  4-Mail-Sequenz; `BREVO_TPL_GENERAL_*` in `N8N_DEPLOYMENT.md` bleibt daher
  bewusst leer, bis dafür Content vorgegeben wird.

---

## Sequenz: `digital-products`

### Mail 1 — sofort — Willkommen + Download-Link

**DE — Betreff:** Willkommen bei ApexCore – hier ist dein Download 🎁

> Hi {{ contact.FIRSTNAME | default: "there" }},
>
> schön, dass du da bist! Dein Download ist startklar:
>
> **[Jetzt herunterladen →]({{ params.DOWNLOAD_URL }})**
>
> Bei Fragen einfach auf diese Mail antworten.
>
> Bis bald,
> Das ApexCore-Team

**EN — Subject:** Welcome to ApexCore – your download is ready 🎁

> Hi {{ contact.FIRSTNAME | default: "there" }},
>
> glad you're here! Your download is ready to go:
>
> **[Download now →]({{ params.DOWNLOAD_URL }})**
>
> Just reply to this email if you have any questions.
>
> Talk soon,
> The ApexCore Team

### Mail 2 — Tag 2 — Was ist ApexCore – Story + Value

**DE — Betreff:** Die Geschichte hinter ApexCore

> Wir haben ApexCore gestartet, weil [Story-Platzhalter: warum wir das tun].
> Unser Ziel: [Value-Proposition-Platzhalter].
>
> In den nächsten Mails zeigen wir dir, wie du das Beste aus deinem Download
> herausholst — und was sonst noch für dich drin ist.

**EN — Subject:** The story behind ApexCore

> We started ApexCore because [story placeholder: why we do this].
> Our goal: [value proposition placeholder].
>
> Over the next few emails we'll show you how to get the most out of your
> download — and what else is in it for you.

### Mail 3 — Tag 4 — Produkt-Highlight + CTA → Gumroad

**DE — Betreff:** Das nächste Level: {{ params.PRODUCT_NAME }}

> Wenn dir der kostenlose Download gefallen hat, wird dir
> **{{ params.PRODUCT_NAME }}** noch besser gefallen.
>
> **[Jetzt auf Gumroad ansehen →]({{ params.GUMROAD_URL }})**

**EN — Subject:** Level up: {{ params.PRODUCT_NAME }}

> If you liked the free download, you'll love
> **{{ params.PRODUCT_NAME }}** even more.
>
> **[Check it out on Gumroad →]({{ params.GUMROAD_URL }})**

### Mail 4 — Tag 7 — Social Proof + Upsell

**DE — Betreff:** Das sagen andere Kunden …

> "[Testimonial-Platzhalter]" — Kunde X
>
> Über 500+ Downloads, durchschnittlich 4.8/5 Sterne.
>
> **[Jetzt upgraden →]({{ params.GUMROAD_URL }})**

**EN — Subject:** Here's what other customers say…

> "[Testimonial placeholder]" — Customer X
>
> 500+ downloads, averaging 4.8/5 stars.
>
> **[Upgrade now →]({{ params.GUMROAD_URL }})**

---

## Sequenz: `ecom-merch`

### Mail 1 — sofort — Willkommen + 10% Rabatt-Code

**DE — Betreff:** Willkommen! Hier sind deine 10% 🎉

> Hi {{ contact.FIRSTNAME | default: "there" }},
>
> als Willkommensgeschenk: **10% Rabatt** mit dem Code
> **`WELCOME10`** auf deine erste Bestellung.
>
> **[Jetzt shoppen →]({{ params.SHOP_URL }})**

**EN — Subject:** Welcome! Here's your 10% off 🎉

> Hi {{ contact.FIRSTNAME | default: "there" }},
>
> as a welcome gift: **10% off** your first order with code
> **`WELCOME10`**.
>
> **[Shop now →]({{ params.SHOP_URL }})**

### Mail 2 — Tag 2 — Bestseller vorstellen

**DE — Betreff:** Unsere Bestseller — von Kunden geliebt

> Diese Produkte verkaufen sich am schnellsten:
>
> - [Bestseller 1]
> - [Bestseller 2]
> - [Bestseller 3]
>
> **[Bestseller ansehen →]({{ params.SHOP_URL }}/bestsellers)**

**EN — Subject:** Our bestsellers — loved by customers

> These are flying off the shelves:
>
> - [Bestseller 1]
> - [Bestseller 2]
> - [Bestseller 3]
>
> **[Shop bestsellers →]({{ params.SHOP_URL }}/bestsellers)**

### Mail 3 — Tag 5 — Trust-Building + Reviews

**DE — Betreff:** Was unsere Kunden sagen

> "[Review-Platzhalter]" ⭐⭐⭐⭐⭐
>
> Schneller Versand, einfache Retoure, persönlicher Support.
>
> **[Jetzt entdecken →]({{ params.SHOP_URL }})**

**EN — Subject:** What our customers say

> "[Review placeholder]" ⭐⭐⭐⭐⭐
>
> Fast shipping, easy returns, real support.
>
> **[Explore now →]({{ params.SHOP_URL }})**

### Mail 4 — Tag 8 — Last-Chance Offer / neuer Drop

**DE — Betreff:** Letzte Chance: dein Rabatt läuft ab

> Dein `WELCOME10`-Code läuft in 48 Stunden ab — und wir haben einen neuen
> Drop: **[Neuer Drop-Name]**.
>
> **[Jetzt sichern →]({{ params.SHOP_URL }})**

**EN — Subject:** Last chance: your discount expires soon

> Your `WELCOME10` code expires in 48 hours — and we just dropped
> **[New drop name]**.
>
> **[Grab it now →]({{ params.SHOP_URL }})**

---

## Hinweise

- Platzhalter in `[...]` müssen vor dem Live-Schalten mit echtem Content
  (Story, Testimonials, Produktnamen) befüllt werden.
- `{{ params.* }}` Variablen werden beim transaktionalen Versand (Mail 1 via
  n8n) oder über Automation-Attribute (Mail 2–4) befüllt.
- Jede DE/EN-Variante als eigenes Template anlegen, Automation verzweigt per
  `LANGUAGE`-Attribut.
