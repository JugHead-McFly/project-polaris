import json
from pathlib import Path

CATALOG_PATH = Path(__file__).parent / "data" / "objects.json"

def normalize_name(name: str) -> str:
    return (name or "").upper().replace("MESSIER", "M").replace(" ", "")

def load_catalog():
    with open(CATALOG_PATH, "r") as f:
        return json.load(f)

def lookup_object(name: str):
    wanted = normalize_name(name)
    for obj in load_catalog():
        candidates = [obj["id"]] + obj.get("aliases", [])
        if wanted in [normalize_name(c) for c in candidates]:
            return obj
    return {
        "id": name or "",
        "common_name": "",
        "type": "",
        "constellation": "",
        "best_months": [],
        "moon_tolerance": "",
        "dwarf_suitability": "",
        "recommended_integration_hours": ""
    }
