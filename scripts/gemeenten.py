#!/usr/bin/env python3
"""
Gedeelde gemeente-configuratie voor het Lokaal Dashboard.

Eén plek waar staat welke gemeenten het dashboard toont. Zowel de CBS-ETL
(fetch_cbs_data.py) als de geometrie-ophaler (fetch_geojson.py) lezen deze
lijst, zodat een nieuwe gemeente toevoegen neerkomt op één regel hieronder.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Gemeenten in het dashboard
#   slug  = interne naam, gebruikt in bestandsnamen en de ?gemeente=-parameter
#   naam  = weergavenaam in de interface
#   code  = CBS-gemeentecode (GMxxxx)
# ---------------------------------------------------------------------------

GEMEENTEN = [
    {"slug": "baarn",      "naam": "Baarn",      "code": "GM0308"},
    {"slug": "woudenberg", "naam": "Woudenberg", "code": "GM0351"},
]

# Gemeente die het dashboard toont zonder ?gemeente=-parameter
STANDAARD_SLUG = "baarn"


def buurt_prefix(gemeente: dict) -> str:
    """CBS-buurtcodeprefix van een gemeente, bijv. GM0308 → BU0308."""
    return "BU" + gemeente["code"][2:]


def geojson_pad(gemeente: dict) -> Path:
    """Pad naar het buurten-GeoJSON van een gemeente (repo-root)."""
    return REPO_ROOT / f"{gemeente['slug']}_buurten.geojson"


def data_pad(gemeente: dict) -> Path:
    """Pad naar het CBS-databestand van een gemeente."""
    return REPO_ROOT / "data" / f"{gemeente['slug']}_social_data.json"


def zoek_gemeente(slug: str) -> dict:
    """Zoek een gemeente op slug; werpt KeyError als die niet bestaat."""
    for gemeente in GEMEENTEN:
        if gemeente["slug"] == slug:
            return gemeente
    raise KeyError(f"Onbekende gemeente: {slug}")
