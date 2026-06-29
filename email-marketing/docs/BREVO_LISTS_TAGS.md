# Brevo Listen, Tags & Segmente (Task 2)

## Listen anlegen

**Contacts → Lists → Create a list**, jeweils im Folder "ApexCore":

| Listenname         | Zweck                                          |
|---------------------|------------------------------------------------|
| `digital-products`  | Gumroad-Käufer, Digital-Product-Waitlist        |
| `ecom-merch`        | Shop-Besucher, Merch-Käufer                     |
| `general-leads`     | Allgemeine Opt-ins ohne spezifische Zuordnung   |
| `vip`               | Repeat-Buyer, High-Value-Kunden                 |

Nach dem Anlegen jeder Liste die **numerische List-ID** aus der URL oder über
**List → Settings** notieren und in `/root/.apexcore.env` eintragen (siehe
`N8N_DEPLOYMENT.md`):

```
BREVO_LIST_DIGITAL_PRODUCTS=<id>
BREVO_LIST_ECOM_MERCH=<id>
BREVO_LIST_GENERAL_LEADS=<id>
BREVO_LIST_VIP=<id>
```

## Contact Attributes ("Tags")

Brevo hat kein freistehendes "Tag"-Feature wie andere ESPs — Tags werden als
**Custom Contact Attributes** abgebildet. Unter **Contacts → Settings →
Contact attributes → Add a new attribute** folgende Attribute anlegen
(Typ: *Text*, außer wo anders angegeben):

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

- [ ] 4 Listen angelegt, IDs in `/root/.apexcore.env` eingetragen
- [ ] Attribute `SOURCE`, `PRODUCT_TYPE`, `LANGUAGE`, `PURCHASED` angelegt
- [ ] Sprach-Segmente für DE/EN je Liste angelegt
