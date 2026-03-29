"use strict";

// =============================================================================
// SOCIAAL DASHBOARD BAARN
// Vanilla JS SPA — Leaflet kaart + Chart.js tijdreeksen + vergelijkingsmodus
// =============================================================================

// ---------------------------------------------------------------------------
// 1. CONSTANTEN & URLS
// ---------------------------------------------------------------------------

const DATA_URL    = "./data/baarn_social_data.json";
const GEOJSON_URL = "https://raw.githubusercontent.com/meijbaard/LocalDashboard/main/baarn_buurten.geojson";

// CBS-kleuren voor de choropleth (van licht → donker)
const KLEUR_SLECHT = ["#ffffb2", "#fed976", "#feb24c", "#fd8d3c", "#f03b20", "#bd0026"];
const KLEUR_GOED   = ["#ffffcc", "#c7e9b4", "#7fcdbb", "#41b6c4", "#2c7fb8", "#253494"];

// Categorie-labels voor de indicator-dropdown groepering
const CATEGORIE_LABELS = {
  armoede:    "Armoede & inkomen",
  inkomen:    "Armoede & inkomen",
  uitkeringen:"Uitkeringen & werk",
  werk:       "Uitkeringen & werk",
  onderwijs:  "Onderwijs",
  jeugd:      "Jeugd & zorg",
  bevolking:  "Bevolking",
};

// ---------------------------------------------------------------------------
// 2. STATE
// ---------------------------------------------------------------------------

const state = {
  data:                null,   // geladen baarn_social_data.json
  geojson:             null,   // geladen GeoJSON
  indicator:           "huishoudens_laag_inkomen",
  jaar:                null,   // string, bijv. "2023"
  geselecteerdeBuurt:  null,   // buurtcode string
  vergelijkingsBuurt:  null,   // buurtcode string
  vergelijkingActief:  false,
};

// ---------------------------------------------------------------------------
// 3. DOM-REFERENTIES
// ---------------------------------------------------------------------------

const el = {
  laadOverlay:         () => document.getElementById("laad-overlay"),
  foutMelding:         () => document.getElementById("fout-melding"),
  foutTekst:           () => document.getElementById("fout-tekst"),
  indicatorSelect:     () => document.getElementById("indicator-select"),
  jaarSelect:          () => document.getElementById("jaar-select"),
  dataJaarLabel:       () => document.getElementById("data-jaar-label"),
  welkomstStaat:       () => document.getElementById("welkomst-staat"),
  buurtStaat:          () => document.getElementById("buurt-staat"),
  buurtNaam:           () => document.getElementById("buurt-naam"),
  buurtMeta:           () => document.getElementById("buurt-meta"),
  sluitBuurtBtn:       () => document.getElementById("sluit-buurt-btn"),
  kaartjesJaar:        () => document.getElementById("kaartjes-jaar"),
  indicatorKaartjes:   () => document.getElementById("indicator-kaartjes"),
  grafiekIndicatorLbl: () => document.getElementById("grafiek-indicator-label"),
  trendGrafiek:        () => document.getElementById("trend-grafiek"),
  vergelijkKnop:       () => document.getElementById("vergelijk-knop"),
  vergelijkKnopTekst:  () => document.getElementById("vergelijk-knop-tekst"),
  vergelijkingPaneel:  () => document.getElementById("vergelijking-paneel"),
  vergelijkingSelect:  () => document.getElementById("vergelijking-select"),
  vergelijkingTabel:   () => document.getElementById("vergelijking-tabel"),
  vglColA:             () => document.getElementById("vgl-col-a"),
  vglColB:             () => document.getElementById("vgl-col-b"),
  vergelijkingRijen:   () => document.getElementById("vergelijking-rijen"),
  legendaTitel:        () => document.getElementById("legenda-titel"),
  legendaItems:        () => document.getElementById("legenda-items"),
};

// ---------------------------------------------------------------------------
// 4. KAART-VARIABELEN
// ---------------------------------------------------------------------------

let kaart       = null;
let geojsonLaag = null;
let trendChart  = null;

// ---------------------------------------------------------------------------
// 5. HULPFUNCTIES
// ---------------------------------------------------------------------------

function getWaarde(buurtCode, indicator, jaar) {
  const buurt = state.data?.buurten?.[buurtCode];
  if (!buurt) return null;
  return buurt.tijdreeksen?.[indicator]?.[jaar] ?? null;
}

function getGemeenteWaarde(indicator, jaar) {
  return state.data?.gemeente?.tijdreeksen?.[indicator]?.[jaar] ?? null;
}

function getIndicatorDef(indicator) {
  return state.data?.metadata?.indicatoren?.[indicator] ?? null;
}

function getActieveJaren(buurtCode, indicator) {
  const buurt = state.data?.buurten?.[buurtCode];
  if (!buurt) return [];
  const tijdreeks = buurt.tijdreeksen?.[indicator] ?? {};
  return Object.keys(tijdreeks)
    .filter(j => tijdreeks[j] !== null)
    .sort();
}

function alleWaardenVoorIndicator(indicator, jaar) {
  if (!state.data) return [];
  return Object.values(state.data.buurten)
    .map(b => b.tijdreeksen?.[indicator]?.[jaar])
    .filter(v => v !== null && v !== undefined);
}

/** Bereken min/max over alle buurten voor een indicator+jaar, met marge. */
function berekenSchaal(indicator, jaar) {
  const waarden = alleWaardenVoorIndicator(indicator, jaar);
  if (!waarden.length) return { min: 0, max: 100 };
  const min = Math.min(...waarden);
  const max = Math.max(...waarden);
  const marge = (max - min) * 0.05 || 1;
  return { min: Math.max(0, min - marge), max: max + marge };
}

/** Interpoleer hex-kleur op basis van genormaliseerde waarde t ∈ [0,1]. */
function interpoleerKleur(schaal, t) {
  const n = schaal.length - 1;
  const pos = t * n;
  const i = Math.min(n - 1, Math.floor(pos));
  const frac = pos - i;

  const parse = hex => [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ];
  const [r1, g1, b1] = parse(schaal[i]);
  const [r2, g2, b2] = parse(schaal[i + 1]);

  const r = Math.round(r1 + (r2 - r1) * frac);
  const g = Math.round(g1 + (g2 - g1) * frac);
  const b = Math.round(b1 + (b2 - b1) * frac);
  return `rgb(${r},${g},${b})`;
}

function getKleur(waarde, schaal, indicatorDef) {
  if (waarde === null || waarde === undefined) return "#cccccc";
  const t = Math.max(0, Math.min(1, (waarde - schaal.min) / (schaal.max - schaal.min)));
  const kleurSchaal = indicatorDef?.hoog_is_slecht ? KLEUR_SLECHT : KLEUR_GOED;
  return interpoleerKleur(kleurSchaal, t);
}

function formateerWaarde(waarde, eenheid) {
  if (waarde === null || waarde === undefined) return "—";
  const geformatteerd = Number.isInteger(waarde)
    ? waarde.toLocaleString("nl-NL")
    : waarde.toLocaleString("nl-NL", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  return `${geformatteerd} ${eenheid ?? ""}`.trim();
}

// ---------------------------------------------------------------------------
// 6. CONTROLS INITIALISEREN
// ---------------------------------------------------------------------------

function initialiseerControls() {
  const meta = state.data.metadata;
  const indicatorEl = el.indicatorSelect();
  const jaarEl = el.jaarSelect();

  // Groepeer indicatoren per categorie
  const groepen = {};
  for (const [key, def] of Object.entries(meta.indicatoren)) {
    const groep = CATEGORIE_LABELS[def.categorie] ?? def.categorie;
    if (!groepen[groep]) groepen[groep] = [];
    groepen[groep].push({ key, def });
  }

  for (const [groepNaam, items] of Object.entries(groepen)) {
    const optgroup = document.createElement("optgroup");
    optgroup.label = groepNaam;
    for (const { key, def } of items) {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = def.label;
      if (key === state.indicator) opt.selected = true;
      optgroup.appendChild(opt);
    }
    indicatorEl.appendChild(optgroup);
  }

  // Jaar-dropdown (nieuwste eerst)
  const jaren = [...meta.jaren].reverse();
  for (const jaar of jaren) {
    const opt = document.createElement("option");
    opt.value = String(jaar);
    opt.textContent = jaar;
    jaarEl.appendChild(opt);
  }

  // Stel standaard jaar in: meest recente jaar met data voor standaard indicator
  state.jaar = String(jaren[0]);
  jaarEl.value = state.jaar;

  el.dataJaarLabel().textContent = `meest recente data: ${jaren[0]}`;

  // Vergelijking-dropdown populeren
  const vglSelect = el.vergelijkingSelect();
  const gesorteerd = Object.entries(state.data.buurten)
    .filter(([, b]) => b.naam)
    .sort(([, a], [, b]) => a.naam.localeCompare(b.naam, "nl"));

  for (const [code, buurt] of gesorteerd) {
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = buurt.naam;
    vglSelect.appendChild(opt);
  }

  // Events
  indicatorEl.addEventListener("change", () => {
    state.indicator = indicatorEl.value;
    updateChoropleth();
    updateLegenda();
    if (state.geselecteerdeBuurt) {
      updateGrafiek();
      updateVergelijkingTabel();
    }
  });

  jaarEl.addEventListener("change", () => {
    state.jaar = jaarEl.value;
    updateChoropleth();
    updateLegenda();
    if (state.geselecteerdeBuurt) {
      updateIndicatorKaartjes();
      updateVergelijkingTabel();
    }
  });
}

// ---------------------------------------------------------------------------
// 7. LEAFLET KAART
// ---------------------------------------------------------------------------

function initialiseerKaart() {
  kaart = L.map("kaart", { zoomControl: true }).setView([52.21, 5.29], 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a>",
  }).addTo(kaart);

  geojsonLaag = L.geoJSON(state.geojson, {
    style: feature => stijlFeature(feature),
    onEachFeature: (feature, layer) => {
      layer.on({
        mouseover: onHover,
        mouseout: onHoverAf,
        click: e => onKlik(e, feature.properties.buurtcode),
      });
    },
  }).addTo(kaart);

  kaart.fitBounds(geojsonLaag.getBounds(), { padding: [20, 20] });
}

function stijlFeature(feature) {
  const code = feature.properties.buurtcode;
  const waarde = getWaarde(code, state.indicator, state.jaar);
  const schaal = berekenSchaal(state.indicator, state.jaar);
  const def = getIndicatorDef(state.indicator);
  const kleur = getKleur(waarde, schaal, def);
  const isGeselecteerd = code === state.geselecteerdeBuurt;
  const isVergelijking = code === state.vergelijkingsBuurt;

  return {
    fillColor: kleur,
    fillOpacity: 0.8,
    color: isGeselecteerd ? "#fec400" : isVergelijking ? "#ff6600" : "#ffffff",
    weight: isGeselecteerd ? 3 : isVergelijking ? 2.5 : 1,
    opacity: 1,
  };
}

function onHover(e) {
  const layer = e.target;
  const props = layer.feature.properties;
  if (props.buurtcode !== state.geselecteerdeBuurt) {
    layer.setStyle({ weight: 2.5, color: "#fec400", fillOpacity: 0.9 });
    layer.bringToFront();
  }
}

function onHoverAf(e) {
  geojsonLaag.resetStyle(e.target);
  // herstel geselecteerde/vergelijkings-stijl
  if (state.geselecteerdeBuurt || state.vergelijkingsBuurt) {
    geojsonLaag.eachLayer(l => {
      const code = l.feature?.properties?.buurtcode;
      if (code === state.geselecteerdeBuurt || code === state.vergelijkingsBuurt) {
        l.setStyle(stijlFeature(l.feature));
      }
    });
  }
}

function onKlik(e, buurtCode) {
  L.DomEvent.stopPropagation(e);

  if (state.vergelijkingActief && state.geselecteerdeBuurt && buurtCode !== state.geselecteerdeBuurt) {
    // Zet als vergelijkingsbuurt
    state.vergelijkingsBuurt = buurtCode;
    el.vergelijkingSelect().value = buurtCode;
    updateChoropleth();
    updateGrafiek();
    updateVergelijkingTabel();
    state.vergelijkingActief = false;
    return;
  }

  selecteerBuurt(buurtCode);
}

function selecteerBuurt(buurtCode) {
  const vorigeKeuze = state.geselecteerdeBuurt;
  state.geselecteerdeBuurt = buurtCode;

  if (buurtCode !== vorigeKeuze) {
    state.vergelijkingsBuurt = null;
    state.vergelijkingActief = false;
    el.vergelijkingPaneel().classList.add("hidden");
    el.vergelijkingTabel().classList.add("hidden");
    el.vergelijkKnopTekst().textContent = "Vergelijk met andere buurt";
  }

  updateChoropleth();
  toonBuurtPaneel(buurtCode);
}

function updateChoropleth() {
  if (!geojsonLaag) return;
  geojsonLaag.eachLayer(l => {
    if (l.feature) l.setStyle(stijlFeature(l.feature));
  });
}

// ---------------------------------------------------------------------------
// 8. LEGENDA
// ---------------------------------------------------------------------------

function updateLegenda() {
  const def = getIndicatorDef(state.indicator);
  if (!def) return;

  const schaal = berekenSchaal(state.indicator, state.jaar);
  const kleurSchaal = def.hoog_is_slecht ? KLEUR_SLECHT : KLEUR_GOED;

  el.legendaTitel().textContent = def.label;

  const stappen = 5;
  const items = [];
  for (let i = stappen; i >= 0; i--) {
    const t = i / stappen;
    const waarde = schaal.min + t * (schaal.max - schaal.min);
    const kleur = interpoleerKleur(kleurSchaal, t);
    items.push({ kleur, waarde });
  }

  el.legendaItems().innerHTML = items.map(({ kleur, waarde }) => `
    <div class="flex items-center gap-2">
      <span class="w-4 h-3 rounded-sm flex-shrink-0" style="background:${kleur}"></span>
      <span class="text-slate-600">${formateerWaarde(waarde, def.eenheid)}</span>
    </div>
  `).join("") + `
    <div class="flex items-center gap-2 mt-1">
      <span class="w-4 h-3 rounded-sm flex-shrink-0 bg-slate-300"></span>
      <span class="text-slate-400">Geen data</span>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 9. ZIJPANEEL
// ---------------------------------------------------------------------------

function toonBuurtPaneel(buurtCode) {
  const buurt = state.data.buurten[buurtCode];
  if (!buurt) return;

  el.welkomstStaat().classList.add("hidden");
  el.buurtStaat().classList.remove("hidden");
  el.buurtStaat().classList.add("flex");

  el.buurtNaam().textContent = buurt.naam || buurtCode;
  el.buurtMeta().textContent = `Buurtcode: ${buurtCode}`;

  updateIndicatorKaartjes();
  updateGrafiek();
}

function sluitBuurtPaneel() {
  state.geselecteerdeBuurt = null;
  state.vergelijkingsBuurt = null;
  state.vergelijkingActief = false;

  el.buurtStaat().classList.add("hidden");
  el.buurtStaat().classList.remove("flex");
  el.welkomstStaat().classList.remove("hidden");
  el.vergelijkingPaneel().classList.add("hidden");
  el.vergelijkingTabel().classList.add("hidden");

  updateChoropleth();
}

function updateIndicatorKaartjes() {
  const code = state.geselecteerdeBuurt;
  if (!code) return;

  el.kaartjesJaar().textContent = `(${state.jaar})`;

  const meta = state.data.metadata.indicatoren;
  const html = Object.entries(meta).map(([key, def]) => {
    const waarde = getWaarde(code, key, state.jaar);
    const gemeenteWaarde = getGemeenteWaarde(key, state.jaar);
    const isActief = key === state.indicator;

    let vergelijkingHtml = "";
    if (gemeenteWaarde !== null) {
      const verschil = waarde !== null ? waarde - gemeenteWaarde : null;
      if (verschil !== null) {
        const positief = def.hoog_is_slecht ? verschil < 0 : verschil > 0;
        const kleur = positief ? "text-emerald-600" : "text-red-500";
        const pijl = verschil > 0 ? "↑" : "↓";
        vergelijkingHtml = `
          <span class="text-xs ${kleur}">
            ${pijl} ${Math.abs(verschil).toLocaleString("nl-NL", { maximumFractionDigits: 1 })}
            vs gem.
          </span>
        `;
      }
    }

    return `
      <div class="rounded-lg p-2.5 cursor-pointer transition-all border
                  ${isActief ? "bg-baarn-100 border-baarn-800" : "bg-slate-50 border-transparent hover:border-slate-200"}"
           onclick="wisselIndicator('${key}')">
        <p class="text-xs text-slate-500 leading-tight">${def.label}</p>
        <p class="font-semibold text-slate-800 text-sm mt-0.5">${formateerWaarde(waarde, def.eenheid)}</p>
        ${vergelijkingHtml}
      </div>
    `;
  }).join("");

  el.indicatorKaartjes().innerHTML = html;
}

function wisselIndicator(key) {
  state.indicator = key;
  el.indicatorSelect().value = key;
  updateChoropleth();
  updateLegenda();
  updateIndicatorKaartjes();
  updateGrafiek();
  updateVergelijkingTabel();
}

// ---------------------------------------------------------------------------
// 10. CHART.JS TIJDREEKS
// ---------------------------------------------------------------------------

function updateGrafiek() {
  const code = state.geselecteerdeBuurt;
  if (!code) return;

  const def = getIndicatorDef(state.indicator);
  if (!def) return;

  el.grafiekIndicatorLbl().textContent = def.label;

  // Verzamel beschikbare jaren
  const alleJaren = state.data.metadata.jaren.map(String);
  const labels = alleJaren;

  const buurtWaarden = alleJaren.map(j => getWaarde(code, state.indicator, j));
  const gemeenteWaarden = alleJaren.map(j => getGemeenteWaarde(state.indicator, j));

  let vergelijkingDataset = null;
  if (state.vergelijkingsBuurt) {
    const vglBuurt = state.data.buurten[state.vergelijkingsBuurt];
    vergelijkingDataset = {
      label: vglBuurt?.naam ?? state.vergelijkingsBuurt,
      data: alleJaren.map(j => getWaarde(state.vergelijkingsBuurt, state.indicator, j)),
      borderColor: "#ff6600",
      backgroundColor: "rgba(255,102,0,0.1)",
      borderWidth: 2,
      tension: 0.3,
      spanGaps: true,
      pointRadius: 3,
    };
  }

  const buurtNaam = state.data.buurten[code]?.naam ?? code;

  const datasets = [
    {
      label: buurtNaam,
      data: buurtWaarden,
      borderColor: "#004a8f",
      backgroundColor: "rgba(0,74,143,0.1)",
      borderWidth: 2.5,
      tension: 0.3,
      spanGaps: true,
      pointRadius: 3,
      pointBackgroundColor: "#004a8f",
    },
    {
      label: "Gem. Baarn",
      data: gemeenteWaarden,
      borderColor: "#94a3b8",
      borderDash: [5, 4],
      borderWidth: 1.5,
      tension: 0.3,
      spanGaps: true,
      pointRadius: 0,
      fill: false,
    },
  ];

  if (vergelijkingDataset) datasets.splice(1, 0, vergelijkingDataset);

  if (trendChart) trendChart.destroy();

  const canvas = el.trendGrafiek();
  trendChart = new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          position: "top",
          labels: { font: { size: 10 }, boxWidth: 12, padding: 6 },
        },
        tooltip: {
          callbacks: {
            label: ctx => {
              const v = ctx.raw;
              return v !== null ? `${ctx.dataset.label}: ${formateerWaarde(v, def.eenheid)}` : null;
            },
          },
        },
      },
      scales: {
        x: {
          ticks: { font: { size: 10 }, maxRotation: 0 },
          grid: { display: false },
        },
        y: {
          ticks: {
            font: { size: 10 },
            callback: v => `${v} ${def.eenheid}`.trim(),
          },
          grid: { color: "#f1f5f9" },
        },
      },
    },
  });
}

// ---------------------------------------------------------------------------
// 11. VERGELIJKINGSMODUS
// ---------------------------------------------------------------------------

function initialiseerVergelijking() {
  el.vergelijkKnop().addEventListener("click", () => {
    if (state.vergelijkingActief) {
      // Annuleer
      state.vergelijkingActief = false;
      el.vergelijkKnopTekst().textContent = "Vergelijk met andere buurt";
      el.vergelijkKnop().classList.remove("bg-baarn-100");
    } else {
      state.vergelijkingActief = true;
      el.vergelijkKnopTekst().textContent = "Klik op de kaart om te vergelijken…";
      el.vergelijkKnop().classList.add("bg-baarn-100");
      el.vergelijkingPaneel().classList.remove("hidden");
    }
  });

  el.vergelijkingSelect().addEventListener("change", () => {
    const code = el.vergelijkingSelect().value;
    state.vergelijkingsBuurt = code || null;
    state.vergelijkingActief = false;
    el.vergelijkKnopTekst().textContent = "Vergelijk met andere buurt";
    el.vergelijkKnop().classList.remove("bg-baarn-100");
    updateChoropleth();
    updateGrafiek();
    updateVergelijkingTabel();
  });
}

function updateVergelijkingTabel() {
  const codeA = state.geselecteerdeBuurt;
  const codeB = state.vergelijkingsBuurt;

  if (!codeA || !codeB) {
    el.vergelijkingTabel().classList.add("hidden");
    return;
  }

  const buurtA = state.data.buurten[codeA];
  const buurtB = state.data.buurten[codeB];
  const meta   = state.data.metadata.indicatoren;

  el.vglColA().textContent = buurtA?.naam ?? codeA;
  el.vglColB().textContent = buurtB?.naam ?? codeB;

  const rijen = Object.entries(meta).map(([key, def]) => {
    const wA = getWaarde(codeA, key, state.jaar);
    const wB = getWaarde(codeB, key, state.jaar);

    const kleurA = (wA !== null && wB !== null)
      ? (def.hoog_is_slecht ? (wA < wB ? "text-emerald-600" : "text-red-500")
                             : (wA > wB ? "text-emerald-600" : "text-red-500"))
      : "";
    const kleurB = (wA !== null && wB !== null)
      ? (def.hoog_is_slecht ? (wB < wA ? "text-emerald-600" : "text-red-500")
                             : (wB > wA ? "text-emerald-600" : "text-red-500"))
      : "";

    return `
      <tr>
        <td class="py-1.5 pr-2 text-slate-500 text-xs leading-tight">${def.label}</td>
        <td class="py-1.5 pr-1 text-right font-medium text-xs ${kleurA}">
          ${formateerWaarde(wA, def.eenheid)}
        </td>
        <td class="py-1.5 text-right font-medium text-xs ${kleurB}">
          ${formateerWaarde(wB, def.eenheid)}
        </td>
      </tr>
    `;
  }).join("");

  el.vergelijkingRijen().innerHTML = rijen;
  el.vergelijkingTabel().classList.remove("hidden");
}

// ---------------------------------------------------------------------------
// 12. DATA LADEN
// ---------------------------------------------------------------------------

async function laadData() {
  try {
    const [dataResp, geojsonResp] = await Promise.all([
      fetch(DATA_URL),
      fetch(GEOJSON_URL),
    ]);

    if (!dataResp.ok) throw new Error(`Sociale data niet gevonden (${dataResp.status})`);
    if (!geojsonResp.ok) throw new Error(`GeoJSON niet gevonden (${geojsonResp.status})`);

    state.data   = await dataResp.json();
    state.geojson = await geojsonResp.json();

  } catch (err) {
    toonFout(err.message);
    throw err;
  }
}

function toonFout(bericht) {
  el.laadOverlay().classList.add("hidden");
  el.foutMelding().classList.remove("hidden");
  el.foutTekst().textContent = bericht;
}

// ---------------------------------------------------------------------------
// 13. INITIALISATIE
// ---------------------------------------------------------------------------

async function init() {
  // Controleer of we op de kaartpagina zijn
  if (!document.getElementById("kaart")) return;

  try {
    await laadData();
  } catch {
    return;
  }

  initialiseerControls();
  initialiseerKaart();
  updateChoropleth();
  updateLegenda();
  initialiseerVergelijking();

  // Sluit-knop zijpaneel
  el.sluitBuurtBtn().addEventListener("click", sluitBuurtPaneel);

  // Verberg laad-overlay
  el.laadOverlay().classList.add("hidden");
}

document.addEventListener("DOMContentLoaded", init);
