# Project Polaris alpha tester pipeline

Status: operator planning aid  
Audience: Doug

Use this file to prevent one quiet tester from stalling alpha progress. Keep
private contact details, exact addresses, invite links, and passwords out of
this file.

## Rules

- Keep only one active tester in setup at a time.
- Keep two or three backup candidates warm enough that alpha does not stall.
- Treat silence after 48-72 hours as permission to identify a backup candidate.
- Treat silence after two weeks from a tester who said yes as stalled, not
  rejected.
- Do not send public group invitations during this private-alpha stage.
- Prioritize testers who can make at least two real observing decisions.

## Status meanings

- **Researching** - possible candidate, no message sent.
- **Invited** - one-to-one message sent, no yes/no yet.
- **Interested** - replied positively, setup details not yet received.
- **Ready to invite** - email, approximate region, rig, and tracking style are
  known.
- **Active** - private invite sent or first visit in progress.
- **Stalled** - no response after the expected follow-up window.
- **Declined** - explicitly not participating.
- **Complete** - first visit and feedback captured.

## Candidate table

| Candidate alias | Region | Likely rig/persona | Status | Why useful | Next action |
| --- | --- | --- | --- | --- | --- |
| Michael G. | UK | Experienced DWARF Mini astrophotographer | Stalled | Strong expert trust check; non-US timezone and global-weather validation | Optional low-pressure close-the-loop note; do not block alpha on him |
| James K. | Philippines | Smart-telescope/lunar imager | Closed | Global weather, timezone, and lunar-planning validation; closed after platform confusion and Android-only fit issue | Do not pursue unless he reopens interest; preserve the browser-app wording lesson |
| Luigi G. | Italy | Thoughtful deep-sky imager comparing Rome light pollution with Sicily Bortle 5 skies | Invited | Excellent fit for light-pollution, darker-site, non-US timezone/weather, and recommendation-trust validation | Wait for response; if interested, collect setup email, approximate observing region, rig, and tracking style |
| Bill W. | United States | DWARF 3 user learning schedule/mosaic workflows | Invited | Strong fit for beginner-to-intermediate clarity, DWARF 3 schedule friction, and US weather/location baseline | Wait for response; if interested, collect setup email, approximate observing region, rig, and tracking style |
| Backup 1 | TBD | TBD | Researching | Keep alpha moving if Luigi or Bill is quiet | Identify from group contributors with thoughtful, practical posts |
| Backup 2 | TBD | TBD | Researching | Avoid single-candidate dependency | Identify a less-expert but real smart-telescope user |

## Setup details to collect after a yes

Ask for:

- email address for the private invitation;
- approximate observing region and country;
- main telescope model;
- usual tracking style: alt-az, EQ, both, or not sure; and
- whether they have a normal weather/planning app they compare against.

Do not ask for:

- password;
- exact home address;
- invite link screenshot;
- access token; or
- raw private account details.

## Candidate selection notes

Prefer people who show at least one of these:

- thoughtful posts about what worked and what did not;
- real smart-telescope imaging experience;
- willingness to share settings or context;
- different geography from Doug's own local sky;
- intermediate experience, not only expert workflows; and
- signs they might return for a second-night test.

Avoid relying only on top-end power users. They are useful for an expert smell
test, but Polaris also needs people who still feel friction in the nightly
decision.

## Follow-up cadence

After sending the first message:

- Wait 48-72 hours before a light follow-up or moving to a backup.
- If they said yes but did not send setup details, one light reminder is enough.
- After two weeks, mark them stalled and keep the door open.

Light stalled-tester note:

> No pressure at all — I know life gets busy. I’m going to keep testing with
> one person at a time, so I may move on to the next tester for now. I’d still
> really value your take whenever timing is easier.

## When a tester says yes

Follow [`NEXT_ALPHA_TESTER_PACKET.md`](NEXT_ALPHA_TESTER_PACKET.md). Paste only
sanitized feedback into the main Codex project task and update
[`ALPHA_TESTER_FLIGHT_LOG.md`](ALPHA_TESTER_FLIGHT_LOG.md).
