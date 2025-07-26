Plan van Aanpak: Buurtendasboard Baarn

Dit document beschrijft de strategie voor het ontwikkelen van een interactief dashboard met kerncijfers voor de buurten in de gemeente Baarn.
Doel

Het creëren van een schaalbaar, interactief dashboard dat geografische data (buurtgrenzen) combineert met actuele, demografische en sociaaleconomische data (CBS-kerncijfers) om een helder en gedetailleerd beeld te geven van de verschillende buurten in Baarn.
Stap 1: Data-analyse en Bronnen

A. GeoJSON-bestand (Geografische data)

We gebruiken het door u aangeleverde baarn_buurten.geojson-bestand, dat gehost wordt op uw GitHub-repository.

    Dit bestand bevat de geometrische data (de "vorm") van alle buurten in Baarn.

    De cruciale eigenschap (property) in dit bestand is de buurtcode (bijv. BU03080000). Dit is de unieke sleutel die we gebruiken om de kaart te koppelen aan de live CBS-data.

    We negeren de overige (statische) CBS-data in dit bestand en vervangen deze door live data.

B. Kerncijfers van het CBS (Live Statistische data)

We gebruiken de OData API van het CBS om de meest recente data rechtstreeks en geautomatiseerd op te halen.

    Dataset: "Kerncijfers wijken en buurten".

    Voordeel: Altijd de meest actuele cijfers, zonder handmatige updates.

Stap 2: Data Ophalen (API-methode)

We focussen ons volledig op de geautomatiseerde API-methode. Dit is de meest robuuste aanpak.

    Endpoint: We gebruiken de OData-URL van de meest recente stabiele CBS-tabel met wijk- en buurtcijfers (bijvoorbeeld die van 2023, 85618NED).

    Filteren: We bouwen in het script een specifieke filter-query op basis van de buurtcodes uit uw GeoJSON-bestand. Dit zorgt ervoor dat we alleen de data opvragen die we nodig hebben en binnen de datalimieten van het CBS blijven.

Stap 3: Het Dashboard Ontwikkelen

De technische opzet is als volgt:

    Basis: Een HTML-pagina.

    Kaart: We gebruiken de JavaScript-bibliotheek Leaflet.js om het baarn_buurten.geojson-bestand te laden en een interactieve kaart van de buurten in Baarn te tonen.

    Data-invoer (de kern):

        Bij het laden van de pagina, sturen we met de fetch() API van JavaScript een verzoek naar de CBS API-URL.

        We ontvangen de actuele data als JSON en slaan deze op in een variabele, klaar voor gebruik.

    Interactie:

        Elke buurt op de kaart wordt klikbaar.

        Wanneer een gebruiker op een buurt klikt:

            We lezen de buurtcode uit de eigenschappen van de aangeklikte buurt op de kaart.

            We zoeken de bijbehorende data die we via de API hebben binnengehaald op basis van deze buurtcode.

            De gevonden live kerncijfers worden overzichtelijk getoond in een informatiepaneel naast de kaart.

        Optioneel: We kunnen grafieken (met Chart.js) toevoegen die een buurt vergelijken met het gemeentelijk gemiddelde.
