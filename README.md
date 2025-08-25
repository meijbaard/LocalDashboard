# 🗺️ Wijkdata Dashboard Gemeente Baarn

Dit project is een interactief dashboard dat wijk- en buurtgegevens voor de gemeente Baarn visualiseert op een kaart. Gebruikers kunnen op specifieke wijken klikken om gedetailleerde demografische en statistische informatie te bekijken.

**[Live voorbeeld](https://cbs.markeijbaard.nl)**

## ✨ Kenmerken

-   **🗺️ Interactieve Kaart**: Een dynamische kaart van Baarn waarop alle wijken en buurten duidelijk zijn aangegeven.
-   **📊 Data Popups**: Door op een wijk te klikken, verschijnt er een popup met overzichtelijke data over die specifieke locatie.
-   **☁️ Dynamische Data**: De geografische en statistische data wordt live geladen vanuit een extern GeoJSON-bestand.
-   **🗑️ Gefilterde Weergave**: Alleen relevante data wordt getoond. Velden met ongeldige waarden (`-99995` of `-99997`) worden automatisch verborgen.
-   **📱 Responsive Design**: De webpagina is geoptimaliseerd voor weergave op zowel desktops als mobiele apparaten.

## 💾 Data Bron

De data voor dit dashboard wordt geladen vanuit het volgende GeoJSON-bestand:
-   **URL**: [`baarn_buurten.geojson`](https://raw.githubusercontent.com/meijbaard/LocalDashboard/main/baarn_buurten.geojson)

Dit bestand bevat zowel de geometrische data (de grenzen van de wijken) als de eigenschappen (de statistische gegevens) per wijk.

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
└─ (data wordt live opgehaald vanaf GitHub)
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
