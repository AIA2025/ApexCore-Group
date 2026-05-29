# Bitcoin Tax & Reporting Kit

**Steuern auf Bitcoin & Krypto: Schritt-für-Schritt-Leitfaden für DACH**  
*Für HODLer, Trader und DeFi-Nutzer in Deutschland, Österreich und der Schweiz*

---

## Über dieses Kit

Dieses Kit hilft dir, deine Bitcoin- und Krypto-Gewinne korrekt zu berechnen, die richtigen Formulare auszufüllen und rechtssicher Steuern zu erklären — ohne teuren Steuerberater für Standardfälle.

**Was du bekommst:**
- Vollständige Schritt-für-Schritt-Anleitung (DE/AT/CH)
- FIFO-Tracker-Template (Excel/CSV)
- Steuer-Checkliste pro Steuerjahr
- Beispielrechnungen (HODLer, Trader, DeFi)
- Muster-Anhang für die Steuererklärung
- FAQ: Die 20 häufigsten Fragen beantwortet

---

## Kapitel 1: Grundlagen — Was ist steuerpflichtig?

### 1.1 Bitcoin als privates Veräußerungsgeschäft (Deutschland)

In Deutschland unterliegen Bitcoin-Gewinne dem **privaten Veräußerungsgeschäft** nach § 23 EStG. Die wesentlichen Regeln:

**Haltefrist:**
- Hältst du Bitcoin **länger als 1 Jahr**, sind Gewinne **steuerfrei** (unabhängig von der Höhe)
- Hältst du kürzer als 1 Jahr, sind Gewinne **steuerpflichtig** — nach deinem persönlichen Einkommensteuersatz (0–45%)

**Freigrenze:**
- Gewinne aus privaten Veräußerungsgeschäften bis **600 EUR/Jahr** sind steuerfrei
- Überschreitest du die 600 EUR, wird der **gesamte Gewinn** versteuert (nicht nur der Anteil über 600 EUR)

**Verluste:**
- Verluste aus Krypto können mit Krypto-Gewinnen des gleichen oder Folgejahres verrechnet werden
- Keine Verrechnung mit anderen Einkunftsarten (z. B. Aktiengewinne, Gehalt)

### 1.2 Österreich: Sonderbesteuerung seit 2022

Seit dem 1. März 2022 gilt in Österreich das neue Ökosozialen Steuerreformgesetz:

- **Keine 1-Jahres-Haltefrist** mehr für Krypto-Assets, die nach dem 28. Feb. 2021 angeschafft wurden
- Einheitlicher **Kapitalertragsteuersatz: 27,5%**
- Altbestand (vor 1. März 2021 angeschafft): bleibt nach alter Regelung steuerfrei nach 1 Jahr
- Verlustausgleich: nur innerhalb der Einkunftsart Kapitalvermögen

### 1.3 Schweiz: Privateigentum vs. Gewerblicher Handel

- Als **Privatperson** sind Krypto-Gewinne in der Schweiz grundsätzlich **steuerfrei**
- Ausnahme: Gewerbsmäßiger Handel (Häufigkeit, Hebel, Anteil am Gesamtvermögen)
- Bitcoin wird im Vermögen mit dem **Jahresend-Kurs** als Vermögenswert deklariert
- Kantonale Unterschiede beachten

---

## Kapitel 2: Welche Transaktionen müssen erfasst werden?

### 2.1 Steuerpflichtige Ereignisse

| Transaktion | Steuerpflichtig? | Hinweis |
|---|---|---|
| BTC kaufen (Fiat → BTC) | Nein | Kauf-Datum und -Preis notieren |
| BTC verkaufen (BTC → Fiat) | **Ja** | Gewinn/Verlust berechnen |
| BTC tauschen (BTC → ETH) | **Ja (DE)** | Gilt als Verkauf |
| BTC als Zahlung erhalten | **Ja** | Wert zum Zeitpunkt = Einnahme |
| Mining-Erträge | **Ja** | Wert bei Zufluss = Einnahme |
| Staking-Rewards | **Ja** | Wert bei Zufluss = Einnahme |
| Lending-Zinsen | **Ja** | Wert bei Zufluss = Einnahme |
| Airdrops | **Ja (wenn Wert > 0)** | Wert bei Zufluss |
| Transfer zwischen eigenen Wallets | Nein | Muss nachweisbar sein |
| Gebühren | Kostenbasis | Erhöhen Einstandspreis |

### 2.2 Nicht steuerpflichtige Ereignisse

- Kauf von Krypto mit Fiat
- Transfer zwischen eigenen Wallets (Nachweis führen!)
- Erhalten von Krypto als Geschenk (unter Freibetrag)

---

## Kapitel 3: Berechnungsmethode — FIFO

Deutschland und Österreich schreiben die **FIFO-Methode** vor (First In, First Out):

> Das zuerst gekaufte Bitcoin wird zuerst verkauft.

### 3.1 FIFO-Beispielrechnung

```
Kauf 1: 0,5 BTC am 01.01.2023 zu 16.000 EUR → Kostenbasis: 8.000 EUR
Kauf 2: 0,5 BTC am 01.06.2023 zu 24.000 EUR → Kostenbasis: 12.000 EUR

Verkauf: 0,5 BTC am 15.01.2024 zu 40.000 EUR → Erlös: 20.000 EUR
→ FIFO: Wir "verkaufen" Kauf 1 (vom 01.01.2023)
→ Haltedauer: 380 Tage > 365 Tage → STEUERFREI
```

### 3.2 Kurzfristiger Gewinn (unter 1 Jahr)

```
Kauf:    0,2 BTC am 01.10.2023 zu 25.000 EUR → 5.000 EUR
Verkauf: 0,2 BTC am 15.03.2024 zu 60.000 EUR → 12.000 EUR
→ Haltedauer: 166 Tage < 365 Tage
→ Gewinn: 12.000 − 5.000 = 7.000 EUR → steuerpflichtig
→ Bei 30% ESt-Satz: 2.100 EUR Steuer
```

---

## Kapitel 4: DeFi — Besonderheiten

### 4.1 Liquidity Pools

- Einzahlen in LP: gilt in DE als Tausch → steuerpflichtiger Vorgang
- LP-Token erhalten: neue Kostenbasis = Wert bei Erhalt
- Rewards aus LP: sofort steuerpflichtig bei Zufluss

### 4.2 Staking & Lending

- Staking-Rewards: Einkünfte aus sonstigen Leistungen
  - 1-Jahres-Frist beginnt neu ab Zufluss
- Lending: Zinserträge = Einnahmen im Jahr des Zuflusses

### 4.3 NFTs

- Kauf mit Krypto: Tausch → steuerpflichtiger Vorgang
- Verkauf: privates Veräußerungsgeschäft wie BTC
- Erstell-Verkauf (Creator): gewerbliche Einkünfte möglich

---

## Kapitel 5: Dokumente & Nachweise

### 5.1 Was aufbewahren?

- Alle Transaktionshistorien (Exchange-Exporte als CSV/PDF)
- Wallet-Adressen und Zugehörigkeit (eigene vs. fremde Wallets)
- Kaufbelege, Verkaufsbelege, Screenshots
- Aufbewahrungsfrist: **10 Jahre** (DE/AT), **10 Jahre** (CH)

### 5.2 Exchange-Exporte

| Exchange | Wo exportieren | Format |
|---|---|---|
| Coinbase | Konto → Statements → Erstellen | CSV |
| Binance | Wallet → Transaktionshistorie | CSV |
| Kraken | Konto → Export | CSV/XLSX |
| Bitpanda | Transaktionen → Exportieren | CSV |
| Ledger Live | Konten → Erweitert → Export | CSV |

### 5.3 DeFi / On-Chain

- Etherscan, BscScan: Wallet-Adresse → Download CSV
- Zerion, DeBank: Portfolio → Export
- Tools: Koinly, CoinTracking, Blockpit (DACH-kompatibel)

---

## Kapitel 6: Steuererklärung ausfüllen

### 6.1 Deutschland — Anlage SO

Gewinne aus privatem Veräußerungsgeschäft werden in der **Anlage SO** eingetragen:

```
Zeile 41: Veräußerungserlöse (gesamt)
Zeile 42: Anschaffungskosten + Werbungskosten
Zeile 43: Gewinn/Verlust (automatisch)
```

**Werbungskosten** (abzugsfähig):
- Transaktionsgebühren (Exchange-Fees)
- Gas-Kosten (Ethereum)
- Anteilige Kosten für Tracking-Software

### 6.2 Österreich — Beilage E1kv

- KESt-pflichtige Krypto-Erträge in **Beilage E1kv** (Kapitalvermögen)
- 27,5% Steuer direkt
- Verluste: Ausgleich innerhalb Kapitalvermögen

### 6.3 Schweiz — Formular Wertschriften

- Krypto-Bestände als Vermögen deklarieren (Jahresend-Kurs)
- Steuerausweis der jeweiligen Kantons-Steuerverwaltung
- Gewinne: in der Regel keine separate Deklaration nötig (Privatvermögen)

---

## Kapitel 7: Häufige Fehler — und wie du sie vermeidest

| Fehler | Konsequenz | Lösung |
|---|---|---|
| Keine Aufzeichnungen geführt | Schätzung durch Finanzamt | Exchange-Historie rückwirkend exportieren |
| FIFO nicht korrekt angewendet | Falsche Steuerberechnung | FIFO-Tracker führen (Template in Kit) |
| Tausch BTC → ETH nicht erfasst | Unversteuerte Gewinne | Jeden Tausch wie Verkauf behandeln |
| Staking-Rewards vergessen | Steuerhinterziehung | Alle Zuflüsse dokumentieren |
| Transfers zwischen eigenen Wallets als Verkauf gewertet | Zu hohe Steuer gezahlt | Nachweis der eigenen Zugehörigkeit |

---

## Kapitel 8: Tools & Software-Empfehlungen

### 8.1 DACH-kompatible Tracking-Tools

| Tool | Preis | Besonderheit |
|---|---|---|
| **Blockpit** | ab 49 EUR/Jahr | Österreichische FIFO, Steuerreport AT/DE |
| **Koinly** | ab 49 USD/Jahr | Beste Exchange-Integration |
| **CoinTracking** | ab 169 USD/Jahr | Seit 2012, umfangreichste Datenbank |
| **Wiso Steuer** | ab 29 EUR | Direktimport für DE-Steuererklärung |
| **ELBA Crypto** | kostenlos | Für einfache Fälle in AT |

### 8.2 Wann zum Steuerberater?

- Mehr als 100 Transaktionen/Jahr
- DeFi, NFTs, Mining in größerem Umfang
- Verdacht auf gewerblichen Handel
- Streit mit dem Finanzamt

---

## Templates & Checklisten

### Template A: FIFO-Tracker (CSV-Struktur)

```csv
Datum,Typ,Coin,Menge,Preis_EUR,Gesamt_EUR,Exchange,Notiz
2023-01-01,BUY,BTC,0.5,16000,8000,Kraken,
2023-06-01,BUY,BTC,0.5,24000,12000,Coinbase,
2024-01-15,SELL,BTC,0.5,40000,20000,Binance,Steuerfrei >1J
2024-03-15,SELL,BTC,0.2,60000,12000,Kraken,Steuerpflichtig
```

### Template B: Jahres-Steuer-Checkliste

- [ ] Alle Exchange-CSVs exportiert und gespeichert
- [ ] Alle On-Chain-Transaktionen (Etherscan etc.) exportiert
- [ ] Eigene Wallet-Transfers dokumentiert und ausgeschlossen
- [ ] FIFO-Tracker aktualisiert
- [ ] Staking/Lending-Erträge erfasst
- [ ] Freigrenze geprüft (600 EUR DE, direkt 27,5% AT)
- [ ] Verluste mit Gewinnen verrechnet
- [ ] Anlage SO / E1kv / Kantonsformular ausgefüllt
- [ ] Belege 10 Jahre aufbewahrt

### Template C: Muster-Zusammenfassung für Steuerberater

```
Steuerjahr: 2024
Steuerpflichtiger: [Name, Adresse, Steuernr.]

Krypto-Transaktionen Übersicht:
─────────────────────────────────────────
Steuerpflichtige Veräußerungen:   7.000 EUR Gewinn
Steuerfreie Veräußerungen (>1J):  20.000 EUR (dokumentiert)
Staking-Erträge:                  150 EUR
Sonstige Erträge:                 0 EUR
─────────────────────────────────────────
Zu versteuerndes Einkommen Krypto: 7.150 EUR
Angewandter Steuersatz:            30% (persönlicher ESt-Satz)
Geschätzte Steuerlast:             2.145 EUR
─────────────────────────────────────────
Anlagen: Exchange-Exporte, FIFO-Tracker (CSV), Wallet-Nachweise
```

---

## FAQ — Die 20 häufigsten Fragen

**1. Muss ich Bitcoin auch dann versteuern, wenn ich noch nicht verkauft habe?**  
Nein. Gewinne entstehen erst bei der Realisierung (Verkauf, Tausch). Solange du hältst, gibt es keine Steuerpflicht.

**2. Was ist, wenn ich meine Kaufbelege nicht mehr habe?**  
Versuche Exchange-Exporte rückwirkend zu laden (die meisten Exchanges halten alle Trades). Als letzten Ausweg kann der Finanzamt-Kurswert zum Zeitpunkt der Anschaffung angesetzt werden.

**3. Gilt die 1-Jahres-Frist auch für Ethereum und andere Altcoins?**  
Ja, in Deutschland gilt § 23 EStG für alle Kryptowährungen.

**4. Ich habe BTC für eine Pizza bezahlt — muss ich das versteuern?**  
Ja, jede Verwendung von BTC (Zahlung, Tausch) ist ein steuerpflichtiges Ereignis.

**5. Was ist mit dem Bitcoin-ETF (z. B. Spot-Bitcoin-ETF)?**  
ETF-Anteile gelten steuerlich wie Aktien (Abgeltungssteuer 26,375%), nicht als direkte Krypto-Haltung.

**6. Wie gehe ich mit Coins um, die ich geschenkt bekommen habe?**  
Schenkungen übernehmen die Kostenbasis und das Anschaffungsdatum des Schenkenden.

**7. Kann ich Verluste aus 2022 (Crashjahr) noch nutzen?**  
In DE: Verlustvorträge sind zeitlich unbegrenzt nutzbar — aber nur mit künftigen Krypto-Gewinnen verrechenbar.

**8. Ich habe mehrere Wallets und Exchanges — muss ich alles zusammenführen?**  
Ja. Das Finanzamt betrachtet alle Bitcoin eines Steuerpflichtigen als einen "Topf" für FIFO-Zwecke (Pooling-Prinzip).

**9. Was passiert, wenn ich nichts angebe?**  
Steuerhinterziehung — bei Nachprüfung: Nachzahlung + Zinsen + Strafzuschlag. Bei Beträgen > 50.000 EUR: strafrechtliche Konsequenzen.

**10. Gibt es eine Selbstanzeige, wenn ich früher nichts angegeben habe?**  
Ja, die strafbefreiende Selbstanzeige nach § 371 AO ist möglich, muss aber vollständig und rechtzeitig erfolgen. Steuerberater hinzuziehen.

**11. Wie werden Hard Forks besteuert (z. B. BCH aus BTC)?**  
Der erhaltene Coin hat zum Zeitpunkt des Erhalts einen Wert → steuerpflichtige Einnahme. Kostenbasis = Wert bei Erhalt.

**12. Was ist mit Wrapped Token (z. B. wBTC)?**  
Wrapping gilt als Tausch — steuerpflichtiges Ereignis in DE.

**13. Gelten NFT-Gewinne genauso wie BTC-Gewinne?**  
Grundsätzlich ja (§ 23 EStG), aber bei Erstellern (Creator) kann gewerbliche Tätigkeit vorliegen.

**14. Ich nutze ein Ledger Hardware Wallet — ändert das etwas?**  
Nein. Die Art der Verwahrung (Hardware, Software, Exchange) ändert nichts an der Steuerpflicht.

**15. Welcher Kurs gilt bei Tauschgeschäften (BTC → ETH)?**  
Der Marktwert zum Zeitpunkt des Tauschs in EUR (z. B. CoinGecko historische Daten).

**16. Wie lange muss ich Belege aufbewahren?**  
10 Jahre (DE und AT). CH: ebenfalls 10 Jahre für steuerlich relevante Unterlagen.

**17. Kann ich Kosten für ein Hardware Wallet absetzen?**  
In DE: anteilig als Werbungskosten, wenn ausschließlich für steuerpflichtige Trades genutzt.

**18. Was ist, wenn mein Exchange gehackt wurde und ich Coins verloren habe?**  
Verlust kann steuerlich geltend gemacht werden (Nachweis erforderlich).

**19. Gilt die 1-Jahres-Frist nach Staking-Aktivierung auch für Ethereum nach dem Merge?**  
Nach aktuellem BMF-Schreiben: ETH, die für Staking genutzt wird, hat weiterhin 1-Jahres-Frist (nicht 10 Jahre).

**20. Ich lebe in Deutschland, habe aber auf einer ausländischen Exchange gehandelt — gilt das trotzdem?**  
Ja. Unbegrenzte Steuerpflicht gilt für alle weltweiten Einkünfte von Personen mit Wohnsitz in DE.

---

*Stand: 2024 | Kein Steuerrecht, keine Rechtsberatung. Dieses Kit dient der Information — komplexe Fälle bitte mit einem Steuerberater besprechen.*

*Bitcoin Tax & Reporting Kit — ApexCore | apexcore.group*
