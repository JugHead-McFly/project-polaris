"""Validate the pinned local catalog and update its digest/count manifest.

Refresh procedure: choose/review an upstream revision, replace CSV and license,
edit source.json revision, then run this script and catalog regressions. Never
updates from the network automatically or touches observations.
"""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.deep_sky_catalog import DATA, catalog

if __name__ == '__main__':
    entries, aliases = catalog()
    manifest = json.loads((DATA/'source.json').read_text())
    manifest.update(sha256=hashlib.sha256((DATA/'openngc.csv').read_bytes()).hexdigest(),
                    usable_deep_sky_entries=len(entries), aliases=len(aliases), schema_version=1)
    (DATA/'source.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))
