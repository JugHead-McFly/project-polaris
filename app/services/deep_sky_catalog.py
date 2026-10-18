"""Offline OpenNGC lookup and conservative, time-stratified planning shortlist.

Data: Mattia Verga and contributors, CC-BY-SA-4.0; pinned manifest and license
are shipped beside the CSV. No network calls, observing history writes or presets.
"""
import hashlib
import csv
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from datetime import timedelta
import numpy as np
from astropy.time import Time

DATA = Path(__file__).resolve().parents[1] / "data" / "catalog"
TYPES = {"G": "Galaxy", "GPair": "Galaxy pair", "GTrpl": "Galaxy triplet",
         "GGroup": "Galaxy group", "OCl": "Open cluster", "GCl": "Globular cluster",
         "Cl+N": "Cluster with nebulosity", "PN": "Planetary nebula", "HII": "Emission nebula",
         "DrkN": "Dark nebula", "EmN": "Emission nebula", "Neb": "Nebula",
         "RfN": "Reflection nebula", "SNR": "Supernova remnant"}
# Never replace existing public IDs with the NGC designation.
LEGACY_MESSIER = {1, 8, 11, 13, 16, 17, 20, 22, 27, 31, 33, 42, 45, 51, 57, 63, 64, 78, 97}


from app.core.request_timing import timed

def identifier(value):
    value = value.strip().upper()
    match = re.fullmatch(r"(NGC|IC|M|C)\s*0*(\d+)([A-Z]*)", value)
    if match:
        prefix, number, suffix = match.groups()
        return f"{prefix}{' ' if prefix == 'C' else ''}{int(number)}{suffix}"
    return value


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def position(ra, dec):
    h, m, s = map(float, ra.split(':'))
    d, dm, ds = map(float, dec.lstrip('+-').split(':'))
    if not (0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60 and 0 <= d <= 90 and 0 <= dm < 60 and 0 <= ds < 60):
        raise ValueError("Invalid catalog coordinate")
    degrees = (d+dm/60+ds/3600) * (-1 if dec.startswith('-') else 1)
    if abs(degrees) > 90:
        raise ValueError("Invalid declination")
    return (h+m/60+s/3600)*15, degrees


def parse_rows(rows):
    entries, aliases, duplicates = {}, {}, []
    for row in rows:
        raw_id = identifier(row['Name'])
        if row['Type'] == 'Dup':
            duplicates.append((raw_id, identifier('NGC'+row['NGC']) if row['NGC'] else identifier('IC'+row['IC'])))
            continue
        if row['Type'] not in TYPES:
            continue
        try:
            ra, dec = position(row['RA'], row['Dec'])
        except (ValueError, TypeError):
            continue
        messier = int(row['M']) if row['M'].isdigit() else None
        canonical = f"M{messier}" if messier in LEGACY_MESSIER else raw_id
        if raw_id == 'NGC7000':
            canonical = 'C 20'
        major, minor = number(row['MajAx']), number(row['MinAx'])
        if major is not None and major <= 0: major = None
        if minor is not None and (minor <= 0 or major is None or minor > major): minor = None
        names = [x.strip() for x in row.get('Common names', '').split(',') if x.strip()]
        entry = dict(id=canonical, name=names[0] if names else canonical, ra_degrees=ra,
            dec_degrees=dec, ra=row['RA'].replace(':','h',1).replace(':','m',1)+'s',
            dec=row['Dec'].replace(':','d',1).replace(':','m',1)+'s',
            object_type=TYPES[row['Type']], type_code=row['Type'], constellation=row['Const'],
            major_arcmin=major, minor_arcmin=minor, v_magnitude=number(row['V-Mag']),
            b_magnitude=number(row['B-Mag']), surface_brightness=number(row['SurfBr']),
            source_fields=row.get('Sources',''), aliases=[raw_id, *names],
            source_url='https://github.com/mattiaverga/OpenNGC', settings_verified=False)
        if messier: entry['aliases'].append(f'M{messier}')
        entries[canonical] = entry
        for alias in [canonical, *entry['aliases']]:
            key = identifier(alias)
            if key not in aliases: aliases[key] = canonical
            elif aliases[key] != canonical: aliases[key] = None  # ambiguous names never guessed
    for alias, target in duplicates:
        canonical = aliases.get(target)
        if canonical:
            aliases[alias] = canonical
            entries[canonical]['aliases'].append(alias)
    return entries, aliases


@lru_cache(maxsize=1)
@timed("catalog_load")
def catalog():
    manifest = json.loads((DATA/'source.json').read_text())
    if hashlib.sha256((DATA/'openngc.csv').read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError("Pinned catalog digest mismatch; validate the catalog before use")
    with (DATA/'openngc.csv').open(encoding='utf-8', newline='') as stream:
        entries, aliases = parse_rows(csv.DictReader(stream, delimiter=';'))
    # M45 has no NGC entry. Keep the verified curated SIMBAD entry searchable.
    from app.data.seasonal_targets import SEASONAL_TARGETS
    pleiades = SEASONAL_TARGETS["M45"]
    entries["M45"] = dict(id="M45", name=pleiades["name"], ra=pleiades["ra"], dec=pleiades["dec"],
        ra_degrees=(3+46/60+24.2/3600)*15, dec_degrees=24+6/60+50/3600,
        object_type="Open cluster", type_code="OCl", constellation="Tau",
        major_arcmin=76.86, minor_arcmin=76.86, v_magnitude=None, b_magnitude=None,
        surface_brightness=None, source_fields="Curated SIMBAD position/extent; magnitude not imported",
        aliases=["M45", "Pleiades"], source_url="https://simbad.cds.unistra.fr/simbad/sim-basic?Ident=M45",
        settings_verified=False)
    aliases.update(M45="M45", PLEIADES="M45")
    return entries, aliases


def get_entry(name):
    entries, aliases = catalog()
    return entries.get(aliases.get(identifier(name)))


def search(query='', offset=0, limit=30):
    entries, aliases = catalog()
    key = identifier(query)
    exact = aliases.get(key)
    matches = [e for e in entries.values() if not key or key in identifier(e['id'])
               or any(key in identifier(a) for a in e['aliases'])]
    matches.sort(key=lambda e: (e['id'] != exact, e['id']))
    return dict(source=json.loads((DATA/'source.json').read_text()), total=len(matches),
                offset=offset, items=matches[offset:offset+limit])


def automatic_exclusion(entry, rig):
    """Conservative discovery rules, not measured limiting magnitudes of a rig."""
    if entry['type_code'] in {'GPair', 'GTrpl', 'GGroup', 'DrkN'}:
        return 'Complex or dark object requires individual assessment'
    if entry['major_arcmin'] is None:
        return 'Angular extent unknown'
    magnitude = entry['v_magnitude']
    if magnitude is None:
        return 'Visual magnitude unknown'
    # Small-aperture automatic discovery is deliberately conservative. Search
    # retains the entire corpus, including objects beyond these starter limits.
    if rig is None or rig.aperture_mm is None:
        return 'Equipment aperture unknown'
    limit = 12 if rig.aperture_mm <= 50 else 14
    if magnitude > limit:
        return f'Outside conservative automatic discovery magnitude {limit} limit'
    if rig.focal_length_mm and rig.pixel_size_um:
        pixels = entry['major_arcmin']*60 / (206.265*rig.pixel_size_um/rig.focal_length_mm)
        if pixels < 8:
            return 'Less than eight pixels across at native image scale'
    # No maximum angular size: large targets remain manual mosaic candidates.
    if entry['surface_brightness'] is not None and entry['surface_brightness'] > 24:
        return 'Very low catalog surface brightness; individual assessment required'
    return None


def imaging_suitability(entry, rig, bortle_class=None):
    """Explainable beginner preference, not a predicted SNR or measured rig limit.

    Integrated V magnitude never substitutes for surface brightness. Catalog
    surface brightness is the upstream B-band mean within its B=25 isophote;
    it is not directly compared to a fabricated Bortle sky magnitude.
    """
    if entry is None:
        return {"adjustment": -44, "reasons": ["Imaging suitability metadata is unavailable; conservative uncertainty penalty (-44)."],
                "major_pixels": None, "minor_pixels": None}
    adjustment, reasons = 0, []
    major_pixels = minor_pixels = None
    magnitude = entry['v_magnitude']
    if magnitude is None:
        adjustment -= 6
        reasons.append("Visual magnitude unknown; no brightness advantage assumed (-6).")
    elif magnitude <= 6:
        adjustment += 8
        reasons.append(f"Bright integrated V magnitude {magnitude:g} (+8); extended contrast is assessed separately.")
    elif magnitude <= 9:
        adjustment += 4
        reasons.append(f"Integrated V magnitude {magnitude:g} (+4); not a surface-brightness measurement.")
    if rig and rig.focal_length_mm and rig.pixel_size_um and entry['major_arcmin']:
        scale = 206.265 * rig.pixel_size_um / rig.focal_length_mm
        major_pixels = entry['major_arcmin'] * 60 / scale
        minor_pixels = entry['minor_arcmin'] * 60 / scale if entry['minor_arcmin'] else None
        reasons.append(f"Catalog extent spans about {major_pixels:.0f} native pixels on the long axis" +
                       (f" and {minor_pixels:.0f} on the short axis." if minor_pixels else "; short-axis extent unknown."))
        if major_pixels >= 120:
            adjustment += 8
            reasons.append("Broad native image footprint (+8); no upper-size penalty, mosaics remain eligible.")
        if entry['type_code'] == 'G':
            if major_pixels < 120:
                adjustment -= 8
                reasons.append("Compact galaxy footprint lowers beginner framing preference (-8).")
            if minor_pixels is None:
                adjustment -= 12
                reasons.append("Galaxy short-axis sampling unknown; conservative footprint penalty (-12).")
            elif minor_pixels < 60:
                adjustment -= 12
                reasons.append("Galaxy spans fewer than 60 native pixels on its short axis (-12).")
    else:
        uncertainty = 20 if entry['type_code'] == 'G' else 8
        adjustment -= uncertainty
        reasons.append(f"Image scale or extent unknown; conservative sampling penalty (-{uncertainty}).")
    if entry['type_code'] in {'G', 'RfN', 'HII', 'EmN', 'Neb', 'SNR', 'PN', 'Cl+N'}:
        surface = entry['surface_brightness']
        if surface is None:
            adjustment -= 8
            reasons.append("Catalog surface brightness unknown; conservative contrast penalty (-8).")
        elif surface >= 23:
            adjustment -= 8
            reasons.append(f"Faint catalog B-band mean surface brightness {surface:g} mag/arcsec² (-8).")
        if (bortle_class is None or bortle_class >= 7) and entry['type_code'] in {'G', 'RfN'}:
            adjustment -= 10
            reasons.append("Bright urban sky or unmeasured sky background reduces confidence in extended broadband detail (-10); this is a preference, not a visibility veto.")
    return {"adjustment": adjustment, "reasons": reasons,
            "major_pixels": major_pixels, "minor_pixels": minor_pixels}


@timed("catalog_shortlist")
def shortlist(context, dark_start, dark_end, rig, completed=(), per_slot=6):
    """Cheap whole-night altitude sieve; detailed Astropy visibility stays decisive.

    Select per 30-minute slot so evening ranking cannot discard later risers.
    32-degree coarse gate allows precession and sampling margin; never authorizes
    a block below the planner's independently calculated 35-degree floor.
    """
    completed_ids = {get_entry(n)['id'] for n in completed if get_entry(n)}
    entries = [e for e in catalog()[0].values()
               if e['id'] not in completed_ids and not automatic_exclusion(e, rig)]
    if not entries: return []
    count = max(2, math.ceil((dark_end-dark_start).total_seconds()/1800)+1)
    times = [dark_start+(dark_end-dark_start)*i/(count-1) for i in range(count)]
    coarse_time = Time(times)
    coarse_time.delta_ut1_utc = 0  # sub-degree sieve only; no IERS download on refresh
    lst = coarse_time.sidereal_time('mean', longitude=context.longitude, model='IAU1982').degree
    ra = np.radians([e['ra_degrees'] for e in entries])
    dec = np.radians([e['dec_degrees'] for e in entries])
    lat = math.radians(context.latitude)
    altitude = np.degrees(np.arcsin(np.clip(np.sin(lat)*np.sin(dec)[None,:]
        + np.cos(lat)*np.cos(dec)[None,:]*np.cos(np.radians(lst)[:,None]-ra[None,:]), -1, 1)))
    selected = set()
    quality = [imaging_suitability(entry, rig, context.bortle_class)['adjustment'] for entry in entries]
    for row in altitude:
        eligible = [i for i, alt in enumerate(row) if alt >= 32]
        eligible.sort(key=lambda i: (-(row[i] - 3*entries[i]['v_magnitude'] + quality[i]), entries[i]['id']))
        # Retain different imaging tradeoffs; a slot full of bright clusters
        # must not erase its best nebula/galaxy before detailed assessment.
        picks = eligible[:max(1, per_slot-3)]
        for family in ({'OCl', 'GCl'}, {'G'}, {'PN', 'HII', 'EmN', 'Neb', 'RfN', 'SNR', 'Cl+N'}):
            if len(picks) >= per_slot:
                break
            choice = next((i for i in eligible if entries[i]['type_code'] in family and i not in picks), None)
            if choice is not None:
                picks.append(choice)
        for i in eligible:
            if len(picks) >= per_slot:
                break
            if i not in picks:
                picks.append(i)
        selected.update(entries[i]['id'] for i in picks)
    return sorted(selected)
