# SOP: Product Kit Workflow — ApexCore

## Eingangsformat

Codex liefert: `<product-name>.md`  
Vollständiger Inhalt mit H1–H3, Bullet-Listen, Templates, FAQ.

---

## Schritt 1 — Ablage im Repo

```bash
# Verzeichnisstruktur im Repo (lokal)
/products/
├── product_2/
│   ├── security-kit.md
│   └── index.html
├── product_4/
│   ├── bitcoin-tax-reporting-kit.md
│   └── index.html
└── sop.md          ← diese Datei

# Beim VPS nach Deploy
/data/apex-core-central/output/
├── product_2/
│   ├── markdown/security-kit.md
│   └── final/security-kit.pdf
└── product_4/
    ├── markdown/bitcoin-tax-reporting-kit.md
    └── final/bitcoin-tax-reporting-kit.pdf

/opt/apexcore-products/
├── product_2/index.html
└── product_4/index.html
```

---

## Schritt 2 — PDF-Build

```bash
# Generisch (nach deploy-all.sh Ausführung):
build-kit.sh product_4

# Manuell:
pandoc /data/apex-core-central/output/product_4/markdown/bitcoin-tax-reporting-kit.md \
  --pdf-engine=wkhtmltopdf \
  --toc --toc-depth=2 \
  -V margin-top=25mm -V margin-bottom=25mm \
  -V margin-left=20mm -V margin-right=20mm \
  -V fontsize=11pt -V papersize=a4 \
  -o /data/apex-core-central/output/product_4/final/bitcoin-tax-reporting-kit.pdf

# Log: /var/log/apexcore-build.log
```

---

## Schritt 3 — Gumroad

Aus Markdown extrahieren:

| Feld | Quelle |
|---|---|
| **Name** | H1-Titel |
| **Tagline** | Erster Absatz nach H1 |
| **Description** | Abschnitt "Was du bekommst" + Benefits |
| **Price** | 29 EUR (Standard) |
| **File** | PDF-Pfad aus Schritt 2 |
| **URL Slug** | kebab-case des Produkt-Namens |

Checkout-Link als `[[GUMROAD_LINK_PRODUCT_N]]` im `index.html` ersetzen.

---

## Schritt 4 — Website

Neue Seite `products/<product-N>/index.html` im Repo:

- Bestehende `index.html` von Product 2 als Vorlage kopieren
- Folgende Blöcke befüllen aus Markdown:
  - **Hero**: H1, erster Absatz, Preis
  - **Was du bekommst**: Kapitel + Bullet-Liste
  - **Zielgruppe**: Pain Points aus Kit
  - **3 Schritte**: Nutzungs-Flow
  - **FAQ**: 5 Fragen aus FAQ-Abschnitt
- `[[GUMROAD_LINK_PRODUCT_N]]` durch echten Link ersetzen

Deploy via `deploy-all.sh` → Seite landet unter `/opt/apexcore-products/product_N/`

---

## Schritt 5 — QA-Checkliste

- [ ] PDF öffnet korrekt (Schrift, TOC, keine fehlenden Seiten)
- [ ] Gumroad-Link funktioniert (Test-Kauf mit EUR 0)
- [ ] Website-Seite erreichbar, alle Links korrekt
- [ ] Markdown + PDF im Repo oder VPS gesichert
- [ ] build-kit.sh getestet mit Exit-Code 0

---

## Neue Produkte anlegen (Vorlage)

```bash
# 1. Neue Produktnummer vergeben (product_6, product_8, ...)
PRODUCT=product_6
SLUG=mein-neues-kit

# 2. Ordner anlegen
mkdir -p products/$PRODUCT

# 3. Markdown von Codex ablegen
cp ~/codex-output/$SLUG.md products/$PRODUCT/$SLUG.md

# 4. index.html von bestehendem Produkt kopieren & anpassen
cp products/product_4/index.html products/$PRODUCT/index.html
# → Titel, Beschreibung, Gumroad-Link ersetzen

# 5. deploy-all.sh ergänzen (5b-Block kopieren, Pfade anpassen)

# 6. Commit + push → deploy-all.sh auf VPS ausführen
git add products/$PRODUCT/ && git commit -m "feat: add $SLUG product page + kit"
git push origin claude/sharp-brahmagupta-03oc5
```

---

*Letzte Aktualisierung: 2025-05 | ApexCore*
