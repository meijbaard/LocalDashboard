# 🗺️ Wijkdata Dashboard Gemeente Baarn

Dit project is een interactief dashboard dat wijk- en buurtgegevens voor de gemeente Baarn visualiseert op een kaart. Gebruikers kunnen op specifieke wijken klikken om gedetailleerde demografische en statistische informatie te bekijken.

![Schermafbeelding van het Baarn Dashboard](https://placehold.co/800x500/f0f2f5/333?text=Voorbeeld+van+de+Kaart)

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

## 🚀 Hoe te gebruiken

Om dit project lokaal te bekijken, kunt u de repository clonen en het `index.html`-bestand (of de naam van uw HTML-bestand) direct in uw webbrowser openen. Er is geen webserver of build-proces nodig.

```bash
# Clone de repository
git clone [https://github.com/meijbaard/LocalDashboard.git](https://github.com/meijbaard/LocalDashboard.git)

# Navigeer naar de map
cd LocalDashboard

# Open het HTML-bestand in uw browser

# 📂 Bestandsstructuur

.
├── index.html         # Het hoofdbestand van de webpagina
└── baarn_buurten.geojson # Het databestand met wijkgegevens
