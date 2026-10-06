"""Publish compact, deduplicated exposure summaries after a completed NAS archive.

Raw files stay on the NAS. Credentials are Windows DPAPI CurrentUser protected.
Run with --export FILE for a credential-free preview; --pair FILE stores a
downloaded pairing credential and removes that plaintext file after verification.
"""
import argparse
import ctypes
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

SITE = "https://project-polaris-private-alpha.onrender.com"
SESSION = re.compile(r"^DWARF_RAW_(?:TELE|WIDE)_(.+)_EXP_([^_]+)_GAIN_[^_]+_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3})$")
FRAME = re.compile(r"^(.+)_([0-9]+(?:\.[0-9]+)?)s[0-9]+_(.+)_(\d{8}-\d{9})_[^_]+\.fits$", re.I)


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def build_manifest(proofs, timezone_name="America/Phoenix"):
    groups = defaultdict(list)
    seen = set()
    for proof in proofs:
        parts = proof["Relative"].replace("/", "\\").split("\\")
        if len(parts) != 3 or parts[0] != "Astronomy":
            continue
        session, frame = SESSION.fullmatch(parts[1]), FRAME.fullmatch(parts[2])
        if not session or not frame or parts[2].lower().startswith(("failed_", "stacked")):
            continue
        # Same content only counts once across inbox/archive repeats and sessions.
        identity = proof["Hash"]
        if not re.fullmatch(r"[a-f0-9]{64}", identity):
            raise ValueError("Invalid archive proof hash")
        if identity in seen:
            continue
        exposure = float(frame[2])
        if not 0 < exposure <= 3600 or abs(exposure - float(session[2])) > 0.001:
            raise ValueError("Frame exposure differs from its session")
        seen.add(identity)
        groups[parts[1]].append((identity, exposure, frame[3]))
    summaries = []
    for name, frames in sorted(groups.items()):
        session = SESSION.fullmatch(name)
        date = datetime.strptime(session[3], "%Y-%m-%d-%H-%M-%S-%f").replace(tzinfo=ZoneInfo(timezone_name))
        filters = {row[2] for row in frames}
        summaries.append({"source_key": sha("dwarf-mini|" + name), "target": session[1],
            "session_name": name, "captured_at": date.astimezone(timezone.utc).isoformat(),
            "filter_name": next(iter(filters)) if len(filters) == 1 else "Mixed",
            "frame_count": len(frames), "integration_seconds": round(sum(row[1] for row in frames), 6),
            "evidence_hash": sha(json.dumps(sorted(frames), separators=(",", ":")))})
    return {"version": 1, "basis": "verified_raw_frames", "sessions": summaries}


def read_archive(folder):
    runs = sorted(folder.glob("run-*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not runs:
        raise ValueError("No completed archive run")
    with runs[-1].open(encoding="utf-8-sig") as stream:
        last = None
        for line in stream:
            if line.strip():
                last = json.loads(line)
    if not last or last.get("status") != "Complete":
        raise ValueError("Archive publication is not complete; history sync deferred")
    proofs = [json.loads(path.read_text(encoding="utf-8-sig")) for path in sorted(folder.glob("proof-*.json"))]
    return build_manifest(proofs)


def protect(data, decrypt=False):
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    function = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.windll.kernel32.LocalFree(output.data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path(r"G:\Polaris_Workspace\ArchiveHistory"))
    parser.add_argument("--state", type=Path, default=Path(r"G:\Polaris_Workspace\HostedLibrarySync"))
    parser.add_argument("--export", type=Path)
    parser.add_argument("--pair", type=Path)
    args = parser.parse_args()
    args.state.mkdir(parents=True, exist_ok=True)
    credential_path = args.state / "credential.dpapi"
    if args.pair:
        raw = args.pair.read_bytes()
        credential = json.loads(raw)
        from uuid import UUID
        UUID(credential["user_id"])
        if not re.fullmatch(r"[A-Za-z0-9_-]{64}", credential["token"]):
            raise ValueError("Invalid pairing credential")
        encrypted = protect(raw)
        if protect(encrypted, decrypt=True) != raw:
            raise ValueError("Credential protection verification failed")
        credential_path.write_bytes(encrypted)
        args.pair.unlink()  # Only the explicitly supplied downloaded credential.
    manifest = read_archive(args.archive)
    payload = json.dumps(manifest, separators=(",", ":"))
    if args.export:
        args.export.write_text(payload, encoding="utf-8")
        print(json.dumps({"sessions": len(manifest["sessions"]), "hours": round(sum(x["integration_seconds"] for x in manifest["sessions"])/3600, 2)}))
        return
    credential = json.loads(protect(credential_path.read_bytes(), decrypt=True))
    response = httpx.post(f"{SITE}/capture-sync/{credential['user_id']}", content=payload,
        headers={"Authorization": "Bearer " + credential["token"], "Content-Type": "application/json"}, timeout=90,
        follow_redirects=False)
    if response.status_code != 200:
        raise RuntimeError(f"Library sync failed: HTTP {response.status_code}")
    result = response.json()
    result["synced_at"] = datetime.now(timezone.utc).isoformat()
    (args.state / "last-success.json").write_text(json.dumps(result), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
