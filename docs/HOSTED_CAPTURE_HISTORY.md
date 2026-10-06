# NAS history in hosted planning

The hosted planner now accepts an account-owned compact session ledger. The legacy local captures/session tables remain unavailable to hosted planning. No FITS, thumbnails, NAS paths, or local database are uploaded.

`scripts/sync_nas_capture_history.py` reads verified archive proofs after the newest archive run reports Complete. It groups original successful raw FITS exposures by native session, derives duration from exposure metadata in the filenames, excludes failed frames, calibration, thumbnails, stacked/restacked products and stack-only legacy imports, and deduplicates repeated content hashes. This is recorded exposure time, not a quality grade. Historical sessions lacking raw-frame evidence remain uncounted rather than estimated.

Hosted session identity is unique per account/source session. Repeat syncs update the same row and never add its time again. Sync is additive across sessions; absence from a later manifest does not erase previously recorded imaging. Target aliases such as C20 / C 20 / NGC7000 normalize to the same target. Progress is currently combined across filters, with the breakdown retained in the API; goals remain broad existing planning baselines, not filter-specific quality requirements.

## Authentication and isolation

Signed-in users can connect or revoke their importer under Imaging progress. Pairing rotates a random 384-bit credential, valid for one year, scoped only to summary ingestion. Only its SHA-256 is stored server-side. Both new tables enforce tenant ownership with FORCE RLS; runtime has no RLS bypass. The sync endpoint uses the supplied owner ID to establish a tenant context and then verifies that owner's credential before admitting a bounded, schema-validated body. It cannot read other account data or authorize any other API.

The downloaded pairing file is a secret. On Windows, `--pair PATH` validates and encrypts it with DPAPI CurrentUser, verifies decryption, then deletes that exact plaintext download. Credentials and state stay outside Git. Re-pair after expiry or Windows-account migration; never paste credentials into chat.

Example (from repository root using its Python environment):

```
.venv\Scripts\python.exe scripts\sync_nas_capture_history.py --export .cache\capture-preview.json --state .cache\capture-sync
.venv\Scripts\python.exe scripts\sync_nas_capture_history.py --pair C:\Users\Doug\Downloads\polaris-library-pairing.json
```

Default archive proof root: `G:\Polaris_Workspace\ArchiveHistory`. Default private sync state: `G:\Polaris_Workspace\HostedLibrarySync`. The sync never changes NAS/device payloads or archive receipts. A PC-side scheduled task may run it after archive completion; it requires the PC to be on and the owning Windows account available. Failed publication defers sync. The website exposes last successful sync and recorded per-target hours.

## Planning behavior

Hosted `/tonight`, `/planner/tonight`, and `/planner/schedule` use only the authenticated owner's ledger. Reaching the existing integration goal invokes the existing 75-point completed-target penalty. It is a de-prioritization, not a target ban: visibility and other conditions still matter. Catalog settings remain labeled catalog-derived because this ledger has no image-quality analysis. Recommendation provenance retains the progress snapshot used for that plan.

Migration: `20261006_0010`. Tests cover repeat imports, tenant separation, token ownership/expiry, duplicate and conflicting manifests, exposure exclusions, target aliasing, the completed-target score penalty, and visible progress. Production PostgreSQL isolation was additionally checked with rolled-back two-owner fixtures before deployment. The historical resize-chart JavaScript test already references an absent `accuracyChart` block at the preceding commit; it is unrelated to this change and remains obsolete.
