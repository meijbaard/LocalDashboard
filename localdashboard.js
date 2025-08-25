// Wacht tot de volledige HTML-structuur is geladen voordat we beginnen.
document.addEventListener('DOMContentLoaded', function() {
    
    // Check of we op de juiste pagina zijn, om fouten op andere pagina's te voorkomen
    if (!document.getElementById('map')) {
        return;
    }
    
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
            return response.text(); // Eerst als tekst lezen voor betere foutafhandeling
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