---
title: "Wijkdata Dashboard Baarn"
layout: localdashboard
author_profile: false
permalink: /localdashboard/
---

<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wijkdata Dashboard Baarn</title>
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Leaflet CSS & JS for Interactive Map -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    
    <!-- Google Fonts: Public Sans (used by www.baarn.nl) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;700&display=swap" rel="stylesheet">

    <style>
        /* Custom styles inspired by www.baarn.nl */
        :root {
            --baarn-blue: #004a8f;
            --baarn-ochre: #fec400;
        }
        body {
            font-family: 'Public Sans', sans-serif;
            background-color: #f7f7f7; /* Light grey background */
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }
        .content-wrapper {
            flex-grow: 1;
        }
        #map {
            height: 80vh;
            width: 100%;
            border-radius: 0.5rem; /* Slightly less rounded corners */
            z-index: 0;
            border: 1px solid #ddd;
        }
        .leaflet-container {
            background: #f7f7f7;
        }
        
        /* Custom popup styling */
        .leaflet-popup-content-wrapper {
            border-radius: 0.5rem;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            background-color: #fff;
        }
        .leaflet-popup-content {
            margin: 1.25rem;
            font-family: 'Public Sans', sans-serif;
            line-height: 1.6;
            width: 300px !important;
        }
        .leaflet-popup-content h3 {
            margin: 0 0 10px 0;
            color: var(--baarn-blue); /* Baarn Blue */
            font-weight: 700;
        }
        .leaflet-popup-content h4 {
            margin: 14px 0 6px 0;
            color: var(--baarn-blue); /* Baarn Blue */
            font-weight: 700;
        }
        .leaflet-popup-content table {
            width: 100%;
            border-collapse: collapse;
        }
        .leaflet-popup-content td {
            padding: 5px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .leaflet-popup-content tr:last-child td {
            border-bottom: none;
        }
        .leaflet-popup-tip-container {
            width: 40px;
            height: 20px;
        }
        .leaflet-popup-close-button {
            padding: 8px 8px 0 0 !important;
            color: #6b7280;
        }
        .loading-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            background-color: rgba(247, 247, 247, 0.8);
            z-index: 1000;
            border-radius: 0.5rem;
        }
    </style>
</head>
<body class="antialiased text-gray-800">

    <!-- Header bar inspired by Baarn.nl -->
    <header class="bg-[#004a8f] text-white p-4 shadow-md">
        <div class="container mx-auto">
            <h1 class="text-2xl font-bold">Gemeente Baarn</h1>
        </div>
    </header>

    <div class="container mx-auto p-4 md:p-8 content-wrapper">
        <!-- Page Title -->
        <div class="mb-8 text-left">
            <h2 class="text-3xl md:text-4xl font-bold text-gray-900">Wijkdata Dashboard</h2>
            <p class="mt-2 text-lg text-gray-600">Klik op een wijk op de kaart voor meer details.</p>
        </div>

        <!-- Main Content: Map -->
        <main class="w-full relative">
            <div id="map">
                 <div id="loading-indicator" class="loading-overlay">
                    <div class="text-center">
                        <svg class="animate-spin h-8 w-8 text-[#004a8f] mx-auto mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <p class="text-gray-600 font-medium">Kaartgegevens laden...</p>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <footer class="text-center py-4 text-gray-500 text-sm">
        <p>Versie 2024.1</p>
    </footer>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // --- MAP INITIALIZATION ---
            const map = L.map('map').setView([52.21, 5.29], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            }).addTo(map);

            let geojsonLayer;
            const loadingIndicator = document.getElementById('loading-indicator');

            // --- DATA FETCHING ---
            const geoJsonUrl = 'https://raw.githubusercontent.com/meijbaard/LocalDashboard/main/baarn_buurten.geojson';

            fetch(geoJsonUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.text();
                })
                .then(text => {
                    try {
                        const data = JSON.parse(text);
                        loadingIndicator.style.display = 'none';
                        initializeMapLayer(data);
                    } catch (error) {
                        console.error('Fout bij het parsen van GeoJSON data:', error);
                        loadingIndicator.innerHTML = `<p class="text-red-600 font-bold p-4">Kon de kaartgegevens niet verwerken. Het GeoJSON-bestand op GitHub bevat een syntaxisfout.</p>`;
                    }
                })
                .catch(error => {
                    console.error('Fout bij het laden van GeoJSON data:', error);
                    loadingIndicator.innerHTML = `<p class="text-red-600 font-bold p-4">Kon de kaartgegevens niet laden. Controleer de URL en de console voor meer details.</p>`;
                });

            // --- MAP LOGIC ---
            function initializeMapLayer(geoJsonData) {
                // Map keys to human-readable labels and define categories
                const propertyLabels = {
                    'Bevolking': {
                        'aantal_inwoners': 'Aantal Inwoners', 'mannen': 'Mannen', 'vrouwen': 'Vrouwen',
                        'bevolkingsdichtheid_inwoners_per_km2': 'Dichtheid (p/km²)',
                        'percentage_personen_0_tot_15_jaar': '% 0-15 Jaar', 'percentage_personen_15_tot_25_jaar': '% 15-25 Jaar',
                        'percentage_personen_25_tot_45_jaar': '% 25-45 Jaar', 'percentage_personen_45_tot_65_jaar': '% 45-65 Jaar',
                        'percentage_personen_65_jaar_en_ouder': '% 65+ Jaar',
                    },
                    'Huishoudens': {
                        'aantal_huishoudens': 'Aantal', 'gemiddelde_huishoudsgrootte': 'Gem. Grootte',
                        'percentage_eenpersoonshuishoudens': '% Eenpersoons', 'percentage_huishoudens_zonder_kinderen': '% Zonder Kinderen',
                        'percentage_huishoudens_met_kinderen': '% Met Kinderen',
                    },
                    'Herkomst': {
                        'percentage_met_herkomstland_nederland': '% Nederland',
                        'percentage_met_herkomstland_uit_europa_excl_nl': '% Europa (excl. NL)',
                        'percentage_met_herkomstland_buiten_europa': '% Buiten Europa',
                    },
                    'Voertuigen': {
                        'personenautos_totaal': 'Totaal Auto\'s', 'personenautos_per_huishouden': 'Auto\'s per Huishouden',
                        'motortweewielers_totaal': 'Totaal Motoren',
                    },
                    'Algemeen': {
                        'oppervlakte_totaal_in_ha': 'Oppervlakte (ha)', 'oppervlakte_land_in_ha': 'Opp. Land (ha)',
                        'oppervlakte_water_in_ha': 'Opp. Water (ha)', 'omgevingsadressendichtheid': 'Adressendichtheid',
                    }
                };

                // Default style for the neighborhoods
                function style(feature) {
                    return {
                        fillColor: '#004a8f', // Baarn Blue
                        weight: 2,
                        opacity: 1,
                        color: 'white',
                        dashArray: '3',
                        fillOpacity: 0.65
                    };
                }

                // Style for when a neighborhood is hovered over
                function highlightFeature(e) {
                    const layer = e.target;
                    layer.setStyle({
                        weight: 4,
                        color: '#fec400', // Baarn Ochre
                        dashArray: '',
                        fillOpacity: 0.8
                    });
                    if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
                        layer.bringToFront();
                    }
                }

                // Reset style when the mouse leaves a neighborhood
                function resetHighlight(e) {
                    geojsonLayer.resetStyle(e.target);
                }

                // Attach popups and event listeners to each feature
                function onEachFeature(feature, layer) {
                    const properties = feature.properties;
                    let popupContent = `<div>`;
                    popupContent += `<h3 class="text-lg">${properties.buurtnaam}</h3>`;
                    popupContent += `<div class="max-h-48 overflow-y-auto pr-2">`;
                    
                    let hasAnyData = false;

                    for (const category in propertyLabels) {
                        const categoryData = [];
                        for (const key in propertyLabels[category]) {
                            if (properties.hasOwnProperty(key)) {
                                const value = properties[key];
                                if (value !== -99995 && value !== -99997) {
                                    const label = propertyLabels[category][key];
                                    categoryData.push({ label, value });
                                }
                            }
                        }

                        if (categoryData.length > 0) {
                            hasAnyData = true;
                            popupContent += `<h4 class="text-sm font-bold">${category}</h4>`;
                            popupContent += `<table><tbody>`;
                            categoryData.forEach(item => {
                                const formattedValue = typeof item.value === 'number' ? item.value.toLocaleString('nl-NL') : item.value;
                                popupContent += `<tr><td class="pr-4 text-gray-600">${item.label}</td><td class="font-bold text-right">${formattedValue}</td></tr>`;
                            });
                            popupContent += `</tbody></table>`;
                        }
                    }
                    
                    if (!hasAnyData) {
                        popupContent += '<p class="text-gray-500">Geen data beschikbaar voor deze wijk.</p>';
                    }

                    popupContent += `</div></div>`;
                    
                    layer.bindPopup(popupContent, {
                        maxHeight: 300
                    });

                    layer.on({
                        mouseover: highlightFeature,
                        mouseout: resetHighlight,
                    });
                }

                // Add GeoJSON layer to the map
                geojsonLayer = L.geoJSON(geoJsonData, {
                    style: style,
                    onEachFeature: onEachFeature
                }).addTo(map);
                
                // Fit map to the bounds of all neighborhoods
                map.fitBounds(geojsonLayer.getBounds());
            }
        });
    </script>

</body>
</html>
