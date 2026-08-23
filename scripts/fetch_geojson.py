#!/usr/bin/env python3
"""
Haalt de buurtgeometrie per gemeente op bij PDOK (CBS Wijken en Buurten WFS)
en schrijft die weg als <slug>_buurten.geojson in de repo-root.

Gebruik:
    python scripts/fetch_geojson.py                 # alleen ontbrekende bestanden
    python scripts/fetch_geojson.py --force         # alles opnieuw ophalen
    python scripts/fetch_geojson.py woudenberg      # één gemeente

Vereisten:
    pip install requests
"""

import argparse
import json
import sys

import requests

from gemeenten import GEMEENTEN, geojson_pad, zoek_gemeente

# ---------------------------------------------------------------------------
# Configuratie
# ---------------------------------------------------------------------------

PDOK_JAAR = "2025"
PDOK_WFS = f"https://service.pdok.nl/cbs/wijkenbuurten/{PDOK_JAAR}/wfs/v1_0"

# Aantal decimalen voor coördinaten. 6 decimalen ≈ 10 cm nauwkeurig — ruim
# voldoende voor een buurtkaart en scheelt een veelvoud aan bestandsgrootte.
DECIMALEN = 6


def bouw_filter(gemeentecode: str) -> str:
    """OGC fes-filter op gemeentecode (PDOK negeert cql_filter op deze service)."""
    return (
        '<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0">'
        "<fes:PropertyIsEqualTo>"
        "<fes:ValueReference>gemeentecode</fes:ValueReference>"
        f"<fes:Literal>{gemeentecode}</fes:Literal>"
        "</fes:PropertyIsEqualTo>"
        "</fes:Filter>"
    )


def rond_af(coordinaten):
    """Rond coördinaten recursief af; de nesting verschilt per geometrietype."""
    if isinstance(coordinaten, (int, float)):
        return round(coordinaten, DECIMALEN)
    return [rond_af(deel) for deel in coordinaten]


def haal_gemeente(gemeente: dict) -> None:
    pad = geojson_pad(gemeente)
    print(f"\n{gemeente['naam']} ({gemeente['code']}) → {pad.name}")

    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "wijkenbuurten:buurten",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "filter": bouw_filter(gemeente["code"]),
    }

    resp = requests.get(PDOK_WFS, params=params, timeout=180)
    resp.raise_for_status()
    geojson = resp.json()

    features = geojson.get("features", [])
    if not features:
        print("  [fout] Geen buurten teruggekregen — controleer de gemeentecode.")
        sys.exit(1)

    for feature in features:
        feature.pop("id", None)
        geometrie = feature.get("geometry") or {}
        if "coordinates" in geometrie:
            geometrie["coordinates"] = rond_af(geometrie["coordinates"])

    uitvoer = {"type": "FeatureCollection", "features": features}

    with open(pad, "w", encoding="utf-8") as f:
        json.dump(uitvoer, f, ensure_ascii=False)

    grootte = pad.stat().st_size / 1024
    print(f"  {len(features)} buurten opgeslagen ({grootte:.0f} kB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="*", help="gemeente-slug(s); leeg = alle")
    parser.add_argument("--force", action="store_true",
                        help="ook bestanden overschrijven die al bestaan")
    args = parser.parse_args()

    if args.slugs:
        gemeenten = [zoek_gemeente(slug) for slug in args.slugs]
        forceer = True   # expliciet genoemd = expliciet gewenst
    else:
        gemeenten = GEMEENTEN
        forceer = args.force

    print("=" * 60)
    print(f"Buurtgeometrie ophalen — PDOK Wijken en Buurten {PDOK_JAAR}")
    print("=" * 60)

    for gemeente in gemeenten:
        if not forceer and geojson_pad(gemeente).exists():
            print(f"\n{gemeente['naam']}: bestaat al, overgeslagen (--force om te vernieuwen)")
            continue
        haal_gemeente(gemeente)

    print("\nKlaar.")


if __name__ == "__main__":
    main()
