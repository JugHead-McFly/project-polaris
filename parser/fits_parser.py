from astropy.io import fits
from typing import Any, Dict
import re


MESSIER_LOOKUP = {
    "M 8": {"object": "M8", "common_name": "Lagoon Nebula", "type": "Emission Nebula", "constellation": "Sagittarius"},
    "M8": {"object": "M8", "common_name": "Lagoon Nebula", "type": "Emission Nebula", "constellation": "Sagittarius"},
    "M 16": {"object": "M16", "common_name": "Eagle Nebula", "type": "Emission Nebula", "constellation": "Serpens"},
    "M16": {"object": "M16", "common_name": "Eagle Nebula", "type": "Emission Nebula", "constellation": "Serpens"},
    "M 17": {"object": "M17", "common_name": "Omega / Swan Nebula", "type": "Emission Nebula", "constellation": "Sagittarius"},
    "M17": {"object": "M17", "common_name": "Omega / Swan Nebula", "type": "Emission Nebula", "constellation": "Sagittarius"},
    "M 22": {"object": "M22", "common_name": "Great Sagittarius Cluster", "type": "Globular Cluster", "constellation": "Sagittarius"},
    "M22": {"object": "M22", "common_name": "Great Sagittarius Cluster", "type": "Globular Cluster", "constellation": "Sagittarius"},
    "M 31": {"object": "M31", "common_name": "Andromeda Galaxy", "type": "Galaxy", "constellation": "Andromeda"},
    "M31": {"object": "M31", "common_name": "Andromeda Galaxy", "type": "Galaxy", "constellation": "Andromeda"},
    "M 51": {"object": "M51", "common_name": "Whirlpool Galaxy", "type": "Galaxy", "constellation": "Canes Venatici"},
    "M51": {"object": "M51", "common_name": "Whirlpool Galaxy", "type": "Galaxy", "constellation": "Canes Venatici"},
    "M 57": {"object": "M57", "common_name": "Ring Nebula", "type": "Planetary Nebula", "constellation": "Lyra"},
    "M57": {"object": "M57", "common_name": "Ring Nebula", "type": "Planetary Nebula", "constellation": "Lyra"},
}


def _clean_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (int, float, bool)):
        return value
    return str(value).strip()


def _normalize_object_name(raw: str) -> str:
    raw = (raw or "").strip().upper()
    raw = re.sub(r"\s+", " ", raw)
    raw = raw.replace("MESSIER ", "M ")
    return raw


def _target_info(raw_object: str) -> Dict[str, Any]:
    key = _normalize_object_name(raw_object)
    if key in MESSIER_LOOKUP:
        return MESSIER_LOOKUP[key]

    compact = key.replace(" ", "")
    if compact in MESSIER_LOOKUP:
        return MESSIER_LOOKUP[compact]

    return {
        "object": raw_object or "",
        "common_name": "",
        "type": "",
        "constellation": "",
    }


def parse_fits(path: str) -> dict:
    with fits.open(path) as hdul:
        header = hdul[0].header

        raw_header = {}
        comments = {}

        for card in header.cards:
            key = card.keyword
            if not key:
                continue
            raw_header[key] = _clean_value(card.value)
            comments[key] = card.comment or ""

        raw_object = raw_header.get("OBJECT", "")
        target = _target_info(str(raw_object))

        parsed = {
            "project": "Project Polaris",
            "target": target,
            "observation": {
                "object_raw": raw_object,
                "observation_utc": raw_header.get("DATE-OBS", ""),
                "ra": raw_header.get("RA", raw_header.get("CRVAL1", "")),
                "dec": raw_header.get("DEC", raw_header.get("CRVAL2", "")),
            },
            "capture_settings": {
                "integration_seconds": raw_header.get("EXPTIME", raw_header.get("EXPOSURE", raw_header.get("LIVETIME", ""))),
                "gain": raw_header.get("GAIN", ""),
                "mode": raw_header.get("MODE", raw_header.get("EQMODE", "")),
                "filter": raw_header.get("FILTER", ""),
            },
            "equipment": {
                "telescope": raw_header.get("TELESCOP", ""),
                "instrument": raw_header.get("INSTRUME", ""),
                "firmware": raw_header.get("FIRMWARE", raw_header.get("SWCREATE", "")),
                "focal_length_mm": raw_header.get("FOCALLEN", raw_header.get("FOCAL", "")),
                "pixel_size_um": raw_header.get("XPIXSZ", raw_header.get("PIXSIZE", "")),
                "sensor_temp_c": raw_header.get("CCD-TEMP", raw_header.get("TEMPERAT", "")),
                "origin": raw_header.get("ORIGIN", ""),
                "bayer_pattern": raw_header.get("BAYERPAT", ""),
            },
            "image": {
                "width": raw_header.get("NAXIS1", ""),
                "height": raw_header.get("NAXIS2", ""),
            },
            "raw_header": raw_header,
            "header_comments": comments,
        }

        return parsed

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 parser/fits_parser.py path/to/file.fits")
        sys.exit(1)

    print(json.dumps(parse_fits(sys.argv[1]), indent=2))
