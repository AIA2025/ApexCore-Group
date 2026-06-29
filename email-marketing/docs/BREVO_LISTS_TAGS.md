# Brevo Listen, Tags & Segmente (Task 2)

## Listen — angelegt am 29-06-2026 via Brevo API

Folder `ApexCore` (folderId `3`) im Account `marketing@apexcore.group`:

| Listenname         | List-ID | Zweck                                          |
|---------------------|--------|------------------------------------------------|
| `digital-products`  | `4`    | Gumroad-Käufer, Digital-Product-Waitlist        |
| `ecom-merch`        | `5`    | Shop-Besucher, Merch-Käufer                     |
| `general-leads`     | `6`    | Allgemeine Opt-ins ohne spezifische Zuordnung   |
| `vip`               | `7`    | Repeat-Buyer, High-Value-Kunden                 |

Bereits in `N8N_DEPLOYMENT.md` als ENV-Vars eingetragen:

```
BREVO_LIST_DIGITAL_PRODUCTS=4
BREVO_LIST_ECOM_MERCH=5
BREVO_LIST_GENERAL_LEADS=6
BREVO_LIST_VIP=7
```

## Contact Attributes ("Tags") — bereits angelegt am 29-06-2026

Brevo hat kein freistehendes "Tag"-Feature wie andere ESPs — Tags werden als
**Custom Contact Attributes** abgebildet. Via Brevo API angelegt
(`POST /v3/contacts/attributes/normal/{NAME}`):

| Attribut         | Typ      | Werte (Beispiel)                          |
|------------------|----------|--------------------------------------------|
| `SOURCE`         | Text     | `gumroad`, `shop`, `waitlist`, `landing`    |
| `PRODUCT_TYPE`   | Text     | `digital`, `merch`, `bundle`                |
| `LANGUAGE`       | Text     | `DE`, `EN`                                  |
| `PURCHASED`      | Boolean  | `true` / `false` — für Abandoned-Cart-Check |

Diese Attribute werden vom n8n-Opt-in-Workflow (`optin-to-brevo.json`) bei
jedem Kontakt-Upsert gesetzt und vom Abandoned-Cart-Workflow gelesen
(`PURCHASED`).

## Segmente (optional, für gezieltere Kampagnen)

**Contacts → Segments → Create a segment**

| Segmentname              | Bedingung                                            |
|---------------------------|------------------------------------------------------|
| `DE - Digital Products`   | List = `digital-products` AND `LANGUAGE` = `DE`      |
| `EN - Digital Products`   | List = `digital-products` AND `LANGUAGE` = `EN`      |
| `DE - Ecom Merch`         | List = `ecom-merch` AND `LANGUAGE` = `DE`             |
| `EN - Ecom Merch`         | List = `ecom-merch` AND `LANGUAGE` = `EN`             |
| `VIP Candidates`          | Anzahl Käufe ≥ 2 (über Brevo E-Commerce/Order-Tracking oder manuelles Attribut `ORDER_COUNT` ≥ 2) |

## Checkliste

- [x] 4 Listen angelegt, IDs in `N8N_DEPLOYMENT.md` eingetragen
- [x] Attribute `SOURCE`, `PRODUCT_TYPE`, `LANGUAGE`, `PURCHASED` angelegt
- [ ] Sprach-Segmente für DE/EN je Liste angelegt (manuell im Brevo-UI, Segment-API nicht abgedeckt)
