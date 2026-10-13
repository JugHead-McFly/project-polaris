"""Read legacy SQLite backups into a NEW, offline review database.

This is deliberately not a production importer. No app imports, credentials,
network calls, or updates to existing databases. Original rows remain intact.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from uuid import UUID


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def target_name(value):
    value = str(value or "").strip().upper()
    match = re.fullmatch(r"(M|NGC|IC|C)\s*(\d+)", value)
    if match:
        prefix, number = match.groups()
        value = f"{prefix}{int(number)}" if prefix != "C" else f"C {int(number)}"
    return {"NGC7000": "C 20", "NORTH AMERICA NEBULA": "C 20"}.get(value, value)


def read_backup(path):
    path = Path(path).resolve(strict=True)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Source database failed integrity check")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"sessions", "captures", "capture_analyses"} <= tables:
            raise ValueError("Source is not a supported legacy backup")
        db.row_factory = sqlite3.Row
        rows = {name: [dict(r) for r in db.execute(f'SELECT * FROM "{name}"')]
                for name in ("sessions", "captures", "capture_analyses")}
    if before != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError("Source changed during inspection")
    return before, rows


def prepare(sources):
    snapshots = {}
    captures = {}
    for path in sources:
        fingerprint, rows = read_backup(path)
        snapshots[fingerprint] = rows
        for row in rows["captures"]:
            # IDs from the same legacy collection stay stable across backups.
            identity = row.get("polaris_id") or canonical([
                target_name(row.get("object_name")), row.get("filename"), row.get("observation_utc")])
            key = digest(str(identity))
            entry = captures.setdefault(key, {"source_key": key, "versions": [], "flags": []})
            version = {"backup_sha256": fingerprint, "record": row}
            if version not in entry["versions"]:
                entry["versions"].append(version)
    for entry in captures.values():
        versions = [v["record"] for v in entry["versions"]]
        # Prefer explicit integration metadata; never equate one sub's exposure
        # with a whole stack's duration. Preserve every alternate original row.
        chosen = max(versions, key=lambda r: sum(r.get(k) is not None for k in
                     ("total_integration_seconds", "subframe_count", "sub_exposure_seconds")))
        seconds = chosen.get("total_integration_seconds")
        if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
            seconds = None
            entry["flags"].append("integration_unknown")
        entry.update(target=target_name(chosen.get("object_name")),
                     original_observation_time=chosen.get("observation_utc"),
                     reported_integration_seconds=seconds, basis="legacy_stack_metadata",
                     verified_integration_seconds=0)
        for field in ("object_name", "filename", "observation_utc", "total_integration_seconds"):
            values = {canonical(r[field]) for r in versions if r.get(field) is not None}
            if len(values) > 1:
                entry["flags"].append("conflicting_" + field)
        stamp = entry["original_observation_time"] or ""
        if not re.search(r"(?:Z|[+-]\d\d:\d\d)$", stamp):
            entry["flags"].append("timezone_unconfirmed")
    # Same target/day is a review signal, not proof of duplication. Never drop
    # either record or automatically add its hours to the live ledger.
    by_night = {}
    for entry in captures.values():
        day = str(entry["original_observation_time"] or "")[:10]
        by_night.setdefault((entry["target"], day), []).append(entry)
    for group in by_night.values():
        if len(group) > 1:
            for entry in group:
                entry["flags"].append("possible_same_night_overlap")
    return snapshots, list(captures.values())


def stage(sources, destination, owner):
    owner = str(UUID(str(owner)))
    snapshots, captures = prepare(sources)
    destination = Path(destination).resolve()
    # Exclusive create: cannot overwrite a backup, production DB, or prior run.
    with destination.open("xb"):
        pass
    try:
        with sqlite3.connect(destination) as db:
            db.executescript("""
                CREATE TABLE review_metadata(owner_id TEXT NOT NULL, format TEXT NOT NULL);
                CREATE TABLE source_snapshots(backup_sha256 TEXT PRIMARY KEY, original_rows TEXT NOT NULL);
                CREATE TABLE legacy_review(owner_id TEXT NOT NULL, source_key TEXT NOT NULL,
                    target TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(owner_id, source_key));
            """)
            db.execute("INSERT INTO review_metadata VALUES (?,?)", (owner, "polaris-legacy-review-v1"))
            db.executemany("INSERT INTO source_snapshots VALUES (?,?)",
                           [(key, canonical(value)) for key, value in snapshots.items()])
            db.executemany("INSERT INTO legacy_review VALUES (?,?,?,?)",
                           [(owner, row["source_key"], row["target"], canonical(row)) for row in captures])
        return {"source_backups": len(snapshots), "unique_captures": len(captures),
                "targets": len({r["target"] for r in captures}),
                "overlap_review_records": sum("possible_same_night_overlap" in r["flags"] for r in captures),
                "timezone_review_records": sum("timezone_unconfirmed" in r["flags"] for r in captures),
                "production_rows_written": 0, "verified_hours_added": 0}
    except Exception:
        # Do not delete even an incomplete staging artifact automatically.
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--owner", required=True, type=UUID)
    args = parser.parse_args()
    print(json.dumps(stage(args.sources, args.destination, args.owner), indent=2))
