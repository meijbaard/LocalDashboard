# 🗺️ Sociaal Dashboard — Baarn en Woudenberg

Dit project is een interactief dashboard dat CBS-buurtgegevens visualiseert op een kaart. Je kiest bovenin een gemeente, een indicator en een jaar, en klikt op een buurt om de kerncijfers, de trend over de jaren en een vergelijking met een andere buurt te zien.

**[Live voorbeeld](https://cbs.markeijbaard.nl)**

Direct naar één gemeente: `?gemeente=baarn` of `?gemeente=woudenberg`.

## ✨ Kenmerken

-   **🗺️ Interactieve Kaart**: Een dynamische kaart per gemeente waarop alle buurten zijn ingekleurd naar de gekozen indicator.
-   **🏛️ Meerdere gemeenten**: Baarn en Woudenberg in hetzelfde dashboard, omschakelbaar zonder de pagina te herladen.
-   **📊 Zijpaneel per buurt**: Kerncijfers naast het gemeentegemiddelde, een tijdreeks vanaf 2016 en een vergelijking met een tweede buurt.
-   **☁️ Automatische data**: Een maandelijkse GitHub Action haalt de CBS-cijfers opnieuw op.
-   **🗑️ Gefilterde Weergave**: CBS-codes voor ontbrekende of onderdrukte data (`-99995`, `-99997`, `-99999`) worden weggelaten in plaats van als getal getoond.
-   **📱 Responsive Design**: De webpagina is geoptimaliseerd voor weergave op zowel desktops als mobiele apparaten.

## 💾 Data Bronnen

| Wat | Bron | Bestand |
|---|---|---|
| Sociale indicatoren per buurt | CBS StatLine, *Kerncijfers wijken en buurten* (OData) | `data/<gemeente>_social_data.json` |
| Buurtgrenzen | PDOK, *CBS Wijken en Buurten* (WFS) | `<gemeente>_buurten.geojson` |
| Welke gemeenten het dashboard toont | gegenereerd uit `scripts/gemeenten.py` | `data/gemeenten.json` |

Beide databestanden worden gegenereerd; pas ze niet met de hand aan.

## 🔄 Data verversen

```bash
pip install requests
python scripts/fetch_geojson.py     # buurtgrenzen (alleen wat nog ontbreekt)
python scripts/fetch_cbs_data.py    # CBS-cijfers + data/gemeenten.json
```

`fetch_geojson.py` slaat bestaande bestanden over; met `--force` of een expliciete gemeente (`python scripts/fetch_geojson.py woudenberg`) worden ze opnieuw opgehaald.

## ➕ Een gemeente toevoegen

Zet er een regel bij in `GEMEENTEN` in [`scripts/gemeenten.py`](scripts/gemeenten.py) — slug, naam en CBS-gemeentecode — en draai daarna beide scripts hierboven. De frontend leest de gemeentelijst uit `data/gemeenten.json` en heeft verder geen aanpassing nodig.

> Buurten die wel CBS-data hebben maar geen vlak meer op de actuele buurtkaart (opgeheven of samengevoegd), laat de ETL weg: anders staan ze wel in het zijpaneel maar zijn ze niet aanklikbaar op de kaart. Het script meldt welke dat zijn.

## 🛠️ Gebruikte Technologieën

-   **HTML5**: Voor de basisstructuur van de webpagina.
-   **Tailwind CSS**: Voor een moderne en responsive styling.
-   **Leaflet.js**: Een open-source JavaScript-bibliotheek voor interactieve kaarten.
-   **JavaScript**: Voor het laden van de data en het toevoegen van interactiviteit.

---

## 🚀 Snel starten (lokaal)

Repository clonen:

```bash
git clone https://github.com/meijbaard/LocalDashboard.git
cd LocalDashboard
```

Open daarna `index.html` in je browser.  
Werkt `fetch()` niet vanaf `file://`? Start een simpele server:

```bash
# Python 3
python3 -m http.server 8080
# open http://localhost:8080
```

---

## 📁 Structuur

```text
LocalDashboard/
├─ index.html
├─ assets/
│  ├─ css/
│  │  └─ localdashboard.css
│  └─ js/
│     └─ localdashboard.js
├─ scripts/
│  ├─ gemeenten.py          # welke gemeenten het dashboard toont
│  ├─ fetch_geojson.py      # buurtgrenzen via PDOK
│  └─ fetch_cbs_data.py     # CBS-kerncijfers via OData
├─ data/
│  ├─ gemeenten.json
│  ├─ baarn_social_data.json
│  └─ woudenberg_social_data.json
├─ baarn_buurten.geojson
└─ woudenberg_buurten.geojson
```

---

## 🌐 Publiceren met GitHub Pages

**Optie A – Deploy from branch (simpel)**

1) Ga naar **Settings → Pages** van de repo.  
2) Kies *Source* = **Deploy from a branch**, *Branch* = `main`, *Folder* = `/ (root)`.  
3) Voeg (voor de zekerheid) een **lege** `.nojekyll` toe in de root zodat er geen Jekyll-processing gebeurt.  
4) (Optioneel) Custom domain? Voeg een `CNAME`-bestand toe met je domein, bijv. `localdashboard.markeijbaard.nl`.

**Optie B – GitHub Actions (automatisch)**

Maak `.github/workflows/pages.yml` met:

```yaml
name: Deploy LocalDashboard
on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Pages
        uses: actions/configure-pages@v5
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: .
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

---

## 🔒 (Optioneel) Content-Security-Policy

Wil je strakker afdwingen wat geladen mag worden? Voeg in `<head>` van `index.html` een CSP-meta toe (pas aan indien nodig):

```html
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self';
               style-src 'self' https://unpkg.com 'unsafe-inline';
               script-src 'self' https://unpkg.com;
               img-src 'self' data: https://*;
               connect-src 'self' https://raw.githubusercontent.com;
               font-src 'self' data:;">
```

---

## 🐞 Issues & bijdragen

Verbeteringen of bugs? Maak een **issue** of **pull request** aan in deze repo.  
Data-correcties (GeoJSON) zijn extra welkom.

---

## 📄 Licentie

MIT © 2025 Mark Eijbaard
