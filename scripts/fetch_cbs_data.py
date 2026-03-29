#!/usr/bin/env python3
"""
ETL: CBS Kerncijfers wijken en buurten → data/baarn_social_data.json

Haalt sociale indicatoren op voor alle buurten in Baarn (GM0308) via de
CBS OData v3 API. Elk publicatiejaar is een aparte CBS-tabel.

Gebruik:
    python scripts/fetch_cbs_data.py

Vereisten:
    pip install requests
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuratie
# ---------------------------------------------------------------------------

ODATA_CATALOG = "https://opendata.cbs.nl/ODataCatalog/Tables"
ODATA_BASE    = "https://opendata.cbs.nl/ODataApi/odata"

GEMEENTE_CODE = "GM0308"
BUURT_PREFIX  = "BU0308"
MAX_JAREN     = 10   # ophalen van maximaal de laatste N jaarlijkse tabellen

# CBS geeft -99995 / -99997 / -99999 terug voor ontbrekende / onderdrukte data
CBS_GEEN_DATA = {-99995, -99997, -99999}

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "baarn_social_data.json"

# ---------------------------------------------------------------------------
# Indicator-definitie
# key          = interne naam in onze JSON-output
# titel_zoek   = zoekterm in de CBS-kolomtitel (case-insensitive, stabiel
#                over tabel-versies; kolomcodes veranderen jaarlijks)
# ---------------------------------------------------------------------------

INDICATOREN = {
    "huishoudens_laag_inkomen": {
        "titel_zoek": "huishoudens met een laag inkomen",
        "label": "% Huishoudens met laag inkomen",
        "beschrijving": (
            "Percentage huishoudens met een gestandaardiseerd inkomen "
            "onder de lage-inkomensgrens (CBS-definitie)."
        ),
        "eenheid": "%",
        "categorie": "armoede",
        "hoog_is_slecht": True,
    },
    "huishoudens_sociaal_minimum": {
        "titel_zoek": "huish. onder of rond sociaal minimum",
        "label": "% Huishoudens nabij sociaal minimum",
        "beschrijving": (
            "Percentage huishoudens met een inkomen op of onder het "
            "sociaal minimum (bijstandsnorm)."
        ),
        "eenheid": "%",
        "categorie": "armoede",
        "hoog_is_slecht": True,
    },
    "gem_inkomen_huishoudens": {
        "titel_zoek": "gem. gestandaardiseerd inkomen",
        "label": "Gem. gestandaardiseerd inkomen",
        "beschrijving": (
            "Gemiddeld gestandaardiseerd besteedbaar inkomen van "
            "particuliere huishoudens (x 1.000 euro per jaar)."
        ),
        "eenheid": "x€1.000",
        "categorie": "inkomen",
        "hoog_is_slecht": False,
    },
    "bijstandsontvangers": {
        "titel_zoek": "personen per soort uitkering; bijstand",
        "label": "Bijstandsontvangers",
        "beschrijving": (
            "Aantal personen met een algemene bijstandsuitkering "
            "(Participatiewet)."
        ),
        "eenheid": "personen",
        "categorie": "uitkeringen",
        "hoog_is_slecht": True,
    },
    "arbeidsparticipatie": {
        "titel_zoek": "nettoarbeidsparticipatie",
        "label": "Netto arbeidsparticipatie",
        "beschrijving": (
            "Percentage van de beroepsbevolking (15–74 jaar) dat "
            "minstens 1 uur per week betaald werkt."
        ),
        "eenheid": "%",
        "categorie": "werk",
        "hoog_is_slecht": False,
    },
    "opleiding_laag": {
        "titel_zoek": "basisonderwijs, vmbo, mbo1",
        "label": "% Laag opgeleid",
        "beschrijving": (
            "Percentage inwoners met basisonderwijs, vmbo of mbo1 als "
            "hoogst behaald diploma."
        ),
        "eenheid": "%",
        "categorie": "onderwijs",
        "hoog_is_slecht": True,
    },
    "opleiding_middelbaar": {
        "titel_zoek": "havo, vwo, mbo2-4",
        "label": "% Middelbaar opgeleid",
        "beschrijving": (
            "Percentage inwoners met havo, vwo of mbo2–4 als "
            "hoogst behaald diploma."
        ),
        "eenheid": "%",
        "categorie": "onderwijs",
        "hoog_is_slecht": False,
    },
    "opleiding_hoog": {
        "titel_zoek": "hbo, wo",
        "label": "% Hoog opgeleid",
        "beschrijving": (
            "Percentage inwoners met hbo of wo als hoogst behaald diploma."
        ),
        "eenheid": "%",
        "categorie": "onderwijs",
        "hoog_is_slecht": False,
    },
    "jongeren_jeugdzorg": {
        "titel_zoek": "percentage jongeren met jeugdzorg",
        "label": "% Jongeren met jeugdzorg",
        "beschrijving": (
            "Percentage jongeren van 0–23 jaar dat gebruik maakt van "
            "jeugdzorg in natura."
        ),
        "eenheid": "%",
        "categorie": "jeugd",
        "hoog_is_slecht": True,
    },
    "aantal_inwoners": {
        "titel_zoek": "aantal inwoners",
        "label": "Aantal inwoners",
        "beschrijving": "Totaal aantal inwoners in de buurt.",
        "eenheid": "personen",
        "categorie": "bevolking",
        "hoog_is_slecht": False,
    },
}

# ---------------------------------------------------------------------------
# HTTP-hulpfuncties
# ---------------------------------------------------------------------------

session = requests.Session()
session.headers.update({"Accept": "application/json"})


def get_json(url: str, params: dict | None = None, max_retries: int = 3) -> dict:
    """Haal JSON op met automatische retry bij netwerk- of serverfouten."""
    for poging in range(1, max_retries + 1):
        try:
            resp = session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            print(f"  [waarschuwing] Poging {poging}/{max_retries} mislukt: {exc}")
            if poging < max_retries:
                time.sleep(2 ** poging)
            else:
                raise


def schoon_waarde(waarde) -> float | None:
    """Zet CBS-waarde om naar float, of None als het ontbrekende data betreft."""
    if waarde is None:
        return None
    try:
        v = float(waarde)
        return None if int(v) in CBS_GEEN_DATA else round(v, 2)
    except (TypeError, ValueError):
        return None


def schoon_code(code: str) -> str:
    """Strip witruimte van CBS-regiocodes (worden soms met spaties teruggegeven)."""
    return code.strip()


# ---------------------------------------------------------------------------
# CBS tabel-discovery
# ---------------------------------------------------------------------------

def haal_beschikbare_tabellen() -> list[dict]:
    """
    Zoek via de CBS-catalogus alle tabellen met kerncijfers wijken en buurten.
    Geeft een lijst van {identifier, jaar, titel} terug, gesorteerd op jaar (nieuw→oud).
    """
    print("CBS-catalogus raadplegen voor beschikbare tabellen...")
    params = {
        "$filter": "startswith(Title,'Kerncijfers wijken en buurten')",
        "$select": "Identifier,Title,Period",
        "$orderby": "Period desc",
        "$format": "json",
        "$top": "25",
    }
    data = get_json(ODATA_CATALOG, params=params)
    tabellen = []
    for item in data.get("value", []):
        periode = item.get("Period", "")
        if periode and len(periode) >= 4 and periode[:4].isdigit():
            tabellen.append({
                "identifier": item["Identifier"],
                "jaar": int(periode[:4]),
                "titel": item.get("Title", ""),
            })
    tabellen.sort(key=lambda x: x["jaar"], reverse=True)
    geselecteerd = tabellen[:MAX_JAREN]
    print(f"  Gevonden: {[t['jaar'] for t in geselecteerd]}")
    return geselecteerd


# ---------------------------------------------------------------------------
# Kolomresolutie per tabel (titel-matching, stabiel over versies)
# ---------------------------------------------------------------------------

def los_kolommen_op(tabel_id: str) -> dict[str, str]:
    """
    Bepaal voor elke indicator welke CBS-kolomsleutel erbij hoort in *deze* tabel.
    Matcht op kolomtitel (case-insensitive) in plaats van sleutelcode,
    omdat die code jaarlijks verandert.

    Geeft terug: { indicator_key → CBS_kolom_sleutel }
    """
    url = f"{ODATA_BASE}/{tabel_id}/DataProperties"
    try:
        data = get_json(url, params={"$format": "json", "$top": "300"})
    except Exception as exc:
        print(f"  [waarschuwing] DataProperties niet ophaalbaar: {exc}")
        return {}

    # Bouw titel → sleutel map
    titel_naar_col: dict[str, str] = {}
    for item in data.get("value", []):
        key = item.get("Key", "")
        titel = item.get("Title", "").strip().lower()
        if key and titel:
            titel_naar_col[titel] = key

    # Zoek elke indicator
    mapping: dict[str, str] = {}
    for ind_key, ind_def in INDICATOREN.items():
        zoek = ind_def["titel_zoek"].lower()
        # Exact of startswith match
        gevonden = titel_naar_col.get(zoek)
        if not gevonden:
            # Fallback: eerste titel die begint met de zoekterm
            for titel, col in titel_naar_col.items():
                if titel.startswith(zoek) or zoek in titel:
                    gevonden = col
                    break
        if gevonden:
            mapping[ind_key] = gevonden

    return mapping


# ---------------------------------------------------------------------------
# Data ophalen per tabel
# ---------------------------------------------------------------------------

def haal_buurtdata(tabel_id: str, jaar: int) -> tuple[list[dict], dict[str, str]]:
    """
    Haal buurt- en gemeenterijen op uit één CBS-tabel.
    Geeft (rijen, kolom_mapping) terug waarbij kolom_mapping de vertaling is van
    indicator_key → CBS-kolomnaam voor *deze* tabel.
    """
    kolom_mapping = los_kolommen_op(tabel_id)
    if not kolom_mapping:
        print(f"  [overgeslagen] Geen bekende indicatoren in tabel {tabel_id}")
        return [], {}

    cbs_kolommen = list(kolom_mapping.values())
    select = "WijkenEnBuurten," + ",".join(cbs_kolommen)
    filter_ = (
        f"startswith(WijkenEnBuurten,'{BUURT_PREFIX}') or "
        f"startswith(WijkenEnBuurten,'{GEMEENTE_CODE}')"
    )
    # Baarn heeft ≤ 25 rijen per tabel — geen paginering nodig.
    # CBS ODataApi ondersteunt $skip niet; ODataFeed is nodig voor grotere datasets.
    url = f"{ODATA_BASE}/{tabel_id}/TypedDataSet"
    params = {
        "$filter": filter_,
        "$select": select,
        "$format": "json",
        "$top": "200",
    }
    alle_rijen = []
    try:
        data = get_json(url, params=params)
        alle_rijen = data.get("value", [])
    except Exception as exc:
        print(f"  [fout] Kon tabel {tabel_id} niet ophalen: {exc}")

    print(f"  {len(alle_rijen)} rijen — {len(kolom_mapping)}/{len(INDICATOREN)} indicatoren")
    return alle_rijen, kolom_mapping


# ---------------------------------------------------------------------------
# Samenstellen van de datastructuur
# ---------------------------------------------------------------------------

def verwerk_data(tabellen: list[dict]) -> dict:
    """Combineer data van alle tabellen tot de uiteindelijke JSON-structuur."""
    buurten: dict[str, dict] = {}
    gemeente: dict[str, dict[str, float | None]] = {k: {} for k in INDICATOREN}
    alle_jaren: set[int] = set()

    for tabel in tabellen:
        tabel_id = tabel["identifier"]
        jaar = tabel["jaar"]
        print(f"\nTabel {tabel_id} ({jaar})...")

        rijen, kolom_mapping = haal_buurtdata(tabel_id, jaar)
        if not rijen:
            continue

        for rij in rijen:
            code = schoon_code(rij.get("WijkenEnBuurten", ""))

            # Gemeentedata (benchmark)
            if code.startswith(GEMEENTE_CODE):
                for ind_key, cbs_col in kolom_mapping.items():
                    if cbs_col in rij:
                        gemeente[ind_key][str(jaar)] = schoon_waarde(rij[cbs_col])
                alle_jaren.add(jaar)
                continue

            # Buurtdata
            if not code.startswith(BUURT_PREFIX):
                continue

            if code not in buurten:
                buurten[code] = {
                    "naam": code,   # wordt overschreven door GeoJSON
                    "wijkcode": "",
                    "tijdreeksen": {k: {} for k in INDICATOREN},
                }

            for ind_key, cbs_col in kolom_mapping.items():
                if cbs_col in rij:
                    buurten[code]["tijdreeksen"][ind_key][str(jaar)] = \
                        schoon_waarde(rij[cbs_col])

            alle_jaren.add(jaar)

    return {
        "buurten": buurten,
        "gemeente_tijdreeksen": gemeente,
        "alle_jaren": sorted(alle_jaren),
    }


def verrijk_met_geojson(resultaat: dict) -> None:
    """Voeg buurtnamen en wijkcodes toe vanuit het lokale GeoJSON-bestand."""
    geojson_pad = Path(__file__).parent.parent / "baarn_buurten.geojson"
    if not geojson_pad.exists():
        print("[waarschuwing] baarn_buurten.geojson niet gevonden")
        return

    with open(geojson_pad, encoding="utf-8") as f:
        geojson = json.load(f)

    buurten = resultaat["buurten"]
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        code = props.get("buurtcode", "").strip()
        naam = props.get("buurtnaam", code)
        wijkcode = props.get("wijkcode", "")

        if code in buurten:
            buurten[code]["naam"] = naam
            buurten[code]["wijkcode"] = wijkcode
        else:
            # Buurt aanwezig in GeoJSON maar zonder CBS-data (te kleine buurt)
            buurten[code] = {
                "naam": naam,
                "wijkcode": wijkcode,
                "tijdreeksen": {k: {} for k in INDICATOREN},
            }

    print(f"  GeoJSON: {len(buurten)} buurten verrijkt met namen")


# ---------------------------------------------------------------------------
# Hoofd-entry
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Sociaal Dashboard Baarn — CBS Data ETL")
    print(f"Gestart: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    tabellen = haal_beschikbare_tabellen()
    if not tabellen:
        print("[fout] Geen CBS-tabellen gevonden. Afgebroken.")
        sys.exit(1)

    resultaat = verwerk_data(tabellen)
    print("\nGeoJSON-verrijking...")
    verrijk_met_geojson(resultaat)

    output = {
        "metadata": {
            "gegenereerd_op": datetime.now(timezone.utc).isoformat(),
            "bron": "CBS StatLine — Kerncijfers wijken en buurten",
            "gemeente": "Baarn",
            "gemeente_code": GEMEENTE_CODE,
            "jaren": resultaat["alle_jaren"],
            "indicatoren": {
                k: {
                    "label": v["label"],
                    "beschrijving": v["beschrijving"],
                    "eenheid": v["eenheid"],
                    "categorie": v["categorie"],
                    "hoog_is_slecht": v["hoog_is_slecht"],
                }
                for k, v in INDICATOREN.items()
            },
        },
        "gemeente": {
            "naam": "Baarn",
            "code": GEMEENTE_CODE,
            "tijdreeksen": resultaat["gemeente_tijdreeksen"],
        },
        "buurten": resultaat["buurten"],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    n_b = len(output["buurten"])
    n_j = len(output["metadata"]["jaren"])
    jaren = output["metadata"]["jaren"]
    print(f"\n✓ Opgeslagen → {OUTPUT_PATH}")
    print(f"  {n_b} buurten | {n_j} jaar "
          f"({min(jaren, default='–')}–{max(jaren, default='–')})")
    print("=" * 60)


if __name__ == "__main__":
    main()
