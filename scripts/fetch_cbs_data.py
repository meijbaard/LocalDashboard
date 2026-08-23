#!/usr/bin/env python3
"""
ETL: CBS Kerncijfers wijken en buurten → data/<gemeente>_social_data.json

Haalt sociale indicatoren op voor alle buurten van de gemeenten in
scripts/gemeenten.py via de CBS OData v3 API. Elk publicatiejaar is een
aparte CBS-tabel; per tabel wordt één query gedaan voor alle gemeenten
samen. Daarnaast wordt data/gemeenten.json geschreven: het overzicht dat
de frontend gebruikt om de gemeentekeuze te vullen.

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

from gemeenten import (
    GEMEENTEN,
    REPO_ROOT,
    STANDAARD_SLUG,
    buurt_prefix,
    data_pad,
    geojson_pad,
)

# ---------------------------------------------------------------------------
# Configuratie
# ---------------------------------------------------------------------------

ODATA_CATALOG = "https://opendata.cbs.nl/ODataCatalog/Tables"
ODATA_BASE    = "https://opendata.cbs.nl/ODataApi/odata"

MAX_JAREN     = 10   # ophalen van maximaal de laatste N jaarlijkse tabellen

# CBS geeft -99995 / -99997 / -99999 terug voor ontbrekende / onderdrukte data
CBS_GEEN_DATA = {-99995, -99997, -99999}

MANIFEST_PATH = REPO_ROOT / "data" / "gemeenten.json"

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
            "Aandeel van de inwoners van 15 tot 75 jaar met basisonderwijs, "
            "vmbo of mbo1 als hoogst behaald onderwijsniveau. Berekend als "
            "aandeel van de drie onderwijsniveaus samen — CBS publiceert per "
            "buurt alleen aantallen personen."
        ),
        "eenheid": "%",
        "categorie": "onderwijs",
        "hoog_is_slecht": True,
    },
    "opleiding_middelbaar": {
        "titel_zoek": "havo, vwo, mbo2-4",
        "label": "% Middelbaar opgeleid",
        "beschrijving": (
            "Aandeel van de inwoners van 15 tot 75 jaar met havo, vwo of "
            "mbo2–4 als hoogst behaald onderwijsniveau. Berekend als aandeel "
            "van de drie onderwijsniveaus samen — CBS publiceert per buurt "
            "alleen aantallen personen."
        ),
        "eenheid": "%",
        "categorie": "onderwijs",
        "hoog_is_slecht": False,
    },
    "opleiding_hoog": {
        "titel_zoek": "hbo, wo",
        "label": "% Hoog opgeleid",
        "beschrijving": (
            "Aandeel van de inwoners van 15 tot 75 jaar met hbo of wo als "
            "hoogst behaald onderwijsniveau. Berekend als aandeel van de drie "
            "onderwijsniveaus samen — CBS publiceert per buurt alleen "
            "aantallen personen."
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

# CBS geeft het hoogst behaalde onderwijsniveau per buurt als aantallen
# personen (15 tot 75 jaar), niet als percentage. Aantallen zijn tussen buurten
# van verschillende grootte niet te vergelijken, dus rekenen we ze om naar een
# aandeel van de drie niveaus samen.
OPLEIDINGSNIVEAUS = ("opleiding_laag", "opleiding_middelbaar", "opleiding_hoog")

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
# Data ophalen per tabel (alle gemeenten in één query)
# ---------------------------------------------------------------------------

def haal_regiodata(tabel_id: str) -> tuple[list[dict], dict[str, str]]:
    """
    Haal buurt- en gemeenterijen van álle geconfigureerde gemeenten op uit
    één CBS-tabel. Geeft (rijen, kolom_mapping) terug waarbij kolom_mapping de
    vertaling is van indicator_key → CBS-kolomnaam voor *deze* tabel.
    """
    kolom_mapping = los_kolommen_op(tabel_id)
    if not kolom_mapping:
        print(f"  [overgeslagen] Geen bekende indicatoren in tabel {tabel_id}")
        return [], {}

    cbs_kolommen = list(kolom_mapping.values())
    select = "WijkenEnBuurten," + ",".join(cbs_kolommen)

    voorwaarden = []
    for gemeente in GEMEENTEN:
        voorwaarden.append(f"startswith(WijkenEnBuurten,'{buurt_prefix(gemeente)}')")
        voorwaarden.append(f"startswith(WijkenEnBuurten,'{gemeente['code']}')")
    filter_ = " or ".join(voorwaarden)

    # Enkele tientallen rijen per tabel — geen paginering nodig.
    # CBS ODataApi ondersteunt $skip niet; ODataFeed is nodig voor grotere datasets.
    url = f"{ODATA_BASE}/{tabel_id}/TypedDataSet"
    params = {
        "$filter": filter_,
        "$select": select,
        "$format": "json",
        "$top": "500",
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

def lege_verzameling() -> dict:
    return {
        "buurten": {},
        "gemeente_tijdreeksen": {k: {} for k in INDICATOREN},
        "alle_jaren": set(),
    }


def verwerk_data(tabellen: list[dict]) -> dict[str, dict]:
    """
    Combineer data van alle tabellen tot één datastructuur per gemeente.
    Geeft terug: { gemeente_slug → {buurten, gemeente_tijdreeksen, alle_jaren} }
    """
    resultaten = {g["slug"]: lege_verzameling() for g in GEMEENTEN}

    for tabel in tabellen:
        tabel_id = tabel["identifier"]
        jaar = tabel["jaar"]
        print(f"\nTabel {tabel_id} ({jaar})...")

        rijen, kolom_mapping = haal_regiodata(tabel_id)
        if not rijen:
            continue

        for rij in rijen:
            code = schoon_code(rij.get("WijkenEnBuurten", ""))

            for gemeente in GEMEENTEN:
                verzameling = resultaten[gemeente["slug"]]

                # Gemeentedata (benchmark)
                if code.startswith(gemeente["code"]):
                    for ind_key, cbs_col in kolom_mapping.items():
                        if cbs_col in rij:
                            verzameling["gemeente_tijdreeksen"][ind_key][str(jaar)] = \
                                schoon_waarde(rij[cbs_col])
                    verzameling["alle_jaren"].add(jaar)
                    break

                # Buurtdata
                if not code.startswith(buurt_prefix(gemeente)):
                    continue

                buurten = verzameling["buurten"]
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

                verzameling["alle_jaren"].add(jaar)
                break

    return resultaten


def zet_opleiding_om_naar_aandelen(tijdreeksen: dict) -> None:
    """Reken de drie opleidingsniveaus per jaar om van aantallen naar procenten."""
    jaren: set[str] = set()
    for key in OPLEIDINGSNIVEAUS:
        jaren.update(tijdreeksen[key])

    for jaar in jaren:
        waarden = [tijdreeksen[key].get(jaar) for key in OPLEIDINGSNIVEAUS]

        # Alleen omrekenen als alle drie de niveaus bekend zijn: ontbreekt er
        # één, dan klopt de noemer niet en zou het aandeel te hoog uitvallen.
        if None in waarden or sum(waarden) <= 0:
            for key in OPLEIDINGSNIVEAUS:
                if jaar in tijdreeksen[key]:
                    tijdreeksen[key][jaar] = None
            continue

        totaal = sum(waarden)
        for key, waarde in zip(OPLEIDINGSNIVEAUS, waarden):
            tijdreeksen[key][jaar] = round(waarde / totaal * 100, 1)


def verrijk_met_geojson(gemeente: dict, verzameling: dict) -> None:
    """Voeg buurtnamen en wijkcodes toe vanuit het lokale GeoJSON-bestand."""
    pad = geojson_pad(gemeente)
    if not pad.exists():
        print(f"  [waarschuwing] {pad.name} niet gevonden — "
              f"draai eerst scripts/fetch_geojson.py")
        return

    with open(pad, encoding="utf-8") as f:
        geojson = json.load(f)

    buurten = verzameling["buurten"]
    codes_met_geometrie = set()

    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        code = props.get("buurtcode", "").strip()
        if not code:
            continue
        codes_met_geometrie.add(code)
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

    # Opgeheven buurten: wel CBS-data uit oudere jaren, maar geen vlak op de
    # huidige buurtkaart. Die laten we weg — anders staan ze wel in het
    # zijpaneel en de vergelijking, maar zijn ze niet aanklikbaar op de kaart.
    verdwenen = sorted(set(buurten) - codes_met_geometrie)
    for code in verdwenen:
        del buurten[code]
    if verdwenen:
        print(f"  Zonder vlak op de buurtkaart, weggelaten: {', '.join(verdwenen)}")

    print(f"  GeoJSON: {len(buurten)} buurten verrijkt met namen")


def bouw_uitvoer(gemeente: dict, verzameling: dict) -> dict:
    """Zet de verzamelde data om naar de JSON-structuur die de frontend leest."""
    return {
        "metadata": {
            "gegenereerd_op": datetime.now(timezone.utc).isoformat(),
            "bron": "CBS StatLine — Kerncijfers wijken en buurten",
            "gemeente": gemeente["naam"],
            "gemeente_code": gemeente["code"],
            "jaren": sorted(verzameling["alle_jaren"]),
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
            "naam": gemeente["naam"],
            "code": gemeente["code"],
            "tijdreeksen": verzameling["gemeente_tijdreeksen"],
        },
        "buurten": verzameling["buurten"],
    }


def schrijf_manifest() -> None:
    """Schrijf data/gemeenten.json — de gemeentelijst die de frontend inleest."""
    manifest = {
        "standaard": STANDAARD_SLUG,
        "gemeenten": [
            {
                "slug": g["slug"],
                "naam": g["naam"],
                "code": g["code"],
                "data": f"./data/{g['slug']}_social_data.json",
                "geojson": f"./{g['slug']}_buurten.geojson",
            }
            for g in GEMEENTEN
        ],
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"✓ Opgeslagen → {MANIFEST_PATH}")


# ---------------------------------------------------------------------------
# Hoofd-entry
# ---------------------------------------------------------------------------

def main() -> None:
    namen = ", ".join(g["naam"] for g in GEMEENTEN)
    print("=" * 60)
    print(f"Lokaal Dashboard — CBS Data ETL ({namen})")
    print(f"Gestart: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    tabellen = haal_beschikbare_tabellen()
    if not tabellen:
        print("[fout] Geen CBS-tabellen gevonden. Afgebroken.")
        sys.exit(1)

    resultaten = verwerk_data(tabellen)

    for gemeente in GEMEENTEN:
        verzameling = resultaten[gemeente["slug"]]
        print(f"\nGeoJSON-verrijking {gemeente['naam']}...")
        verrijk_met_geojson(gemeente, verzameling)

        zet_opleiding_om_naar_aandelen(verzameling["gemeente_tijdreeksen"])
        for buurt in verzameling["buurten"].values():
            zet_opleiding_om_naar_aandelen(buurt["tijdreeksen"])

        uitvoer = bouw_uitvoer(gemeente, verzameling)
        pad = data_pad(gemeente)
        pad.parent.mkdir(parents=True, exist_ok=True)
        with open(pad, "w", encoding="utf-8") as f:
            json.dump(uitvoer, f, ensure_ascii=False, indent=2)

        jaren = uitvoer["metadata"]["jaren"]
        print(f"✓ Opgeslagen → {pad}")
        print(f"  {len(uitvoer['buurten'])} buurten | {len(jaren)} jaar "
              f"({min(jaren, default='–')}–{max(jaren, default='–')})")

    print()
    schrijf_manifest()
    print("=" * 60)


if __name__ == "__main__":
    main()
