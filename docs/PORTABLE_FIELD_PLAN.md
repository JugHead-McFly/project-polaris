# Portable field plan

The hosted Tonight panel can download a plain-text field checklist and an ICS
calendar file from its currently accepted response. These are advisory snapshots,
not telescope instructions or connected-calendar writes. Opening or downloading
never recalculates Tonight. No account, schema, OAuth or dependency change is needed.
The text can be opened and printed in a text editor; no browser-print implementation
or printer/device compatibility is claimed.

## Evidence and scope

M110's official [changelog](https://github.com/mjm1138/m110/blob/main/CHANGELOG.md)
documents printable field guides and corrections preserving the computed night and
site. That verifies a competitor capability, not adoption or user demand for ICS.
Polaris's Product Bible favors less setup work and explanatory recommendations;
its Voice of Customer does not establish calendar-export demand. Portable copies
reducing manual copying is a hypothesis for Doug to assess.

## Snapshot and time contract

The additive `field_plan` Tonight field is built after the existing plan and, for
hosted POST, after the recommendation run ID is available. It contains bounded text
and calendar strings, a snapshot hash, the observing night, generation timestamp,
and any export-unavailable reason. A serializer failure leaves the plan intact.
GET is still read-only; existing POST recommendation persistence is unchanged.
There is no new endpoint accepting arbitrary snapshots.

Only actual `schedule.blocks` are serialized. Each run remains a separate event,
including setup time; recommended windows, fallback choices and backups are not
converted to events. The text preserves site name, observing timezone and night,
rig, EQ confirmation, decision, source/confidence, reasons, run number, setup and
imaging minutes, notes, and obstruction Off or applied spot/revision/source/review
metadata. Coordinates, full obstruction geometry and authentication data are
omitted. Site/spot names may still be personal: the UI says review before sharing.

The scheduler currently emits date-bearing local wall-clock strings without UTC
offsets. The serializer resolves both folds using the observing site's IANA zone,
round-trips through UTC, and refuses ambiguous/nonexistent times or blocks crossing
a clock change. It also rejects overlapping/reversed blocks, dates inconsistent
with the observing night, unsupported decision-with-blocks, and oversized output.
When darkness bounds are present, their associated sunset date anchors the observing night (dusk date if
sunset is absent);
astronomical dusk itself may be after midnight in summer. After midnight
the scheduler calculation date can be the next local day. The night-reference label explicitly names its date basis (sunset, darkness
start, or schedule date). Calculation date and full darkness bounds are exported,
and every block must fit the actual darkness interval.
Conservatively, **both text and ICS are unavailable** when this validation fails;
it does not silently repair or infer a different schedule. An empty schedule still
has a text decision summary but no calendar events. No-profile planning is unchanged.

Events use UTC start/end and tentative/transparent status, with no alarms,
attendees, invitations or recurring rules. Event IDs derive deterministically from
the same sanitized plan metadata and blocks (including persisted run ID when
present); downloading an unchanged snapshot again preserves IDs. Refreshing a plan
may produce different IDs; importing another file is not a promise to replace old
calendar entries. Generation timestamp is excluded from the hash. There is no
claim calendar applications universally deduplicate imports. Export follows
[RFC 5545](https://www.rfc-editor.org/rfc/rfc5545.html) text escaping, CRLF, and
75-octet UTF-8-safe folding.

## Lifecycle and verification

Hosted download controls clear on loading/errors, Edit home, account changes,
sign-out, setup-spot changes, EQ input changes, and back/forward cache restoration.
A version guard prevents a late plan response from re-enabling export after those
changes. Refresh is required to get a current downloadable snapshot. The local API
also returns field-plan data, but local-mode dashboard download controls are not
part of this bounded first UI integration.

Synthetic tests cover midnight and observing-zone conversion, DST gap/fold/change
rejection, stale dates, separate runs, invalid/oversized output, ICS escaping/folding,
actual saved-spot resolver provenance, real Tonight response serialization, and
export errors preserving the plan. DOM tests cover exact file blobs, resets and
whole-operator lifecycle wiring with synthetic auth/network. They do not establish
browser download handling, real calendar import, printer layout or iPhone behavior.
No real account or external calendar is accessed during validation.
