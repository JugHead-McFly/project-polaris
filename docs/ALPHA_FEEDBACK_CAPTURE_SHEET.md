# Project Polaris alpha feedback capture sheet

Status: live note-taking aid  
Audience: Doug only

Use this during or immediately after a private-alpha tester session. Keep names,
emails, passwords, access tokens, exact addresses, and private account details
out of this file. Transfer only the useful summary into
[`ALPHA_TESTER_FLIGHT_LOG.md`](ALPHA_TESTER_FLIGHT_LOG.md).
Use the sanitized paste-back format in
[`NEXT_ALPHA_TESTER_PACKET.md`](NEXT_ALPHA_TESTER_PACKET.md) when bringing
feedback into the main Codex project task.

## Tester and session

- Tester alias:
- Date:
- Device used:
- Telescope type:
- Approximate observing region:
- First visit or return visit:
- Was Doug watching live, or was this asynchronous feedback?

## What happened

- Did the tester accept the invite?
- Did sign-in work without help?
- Did setup open on the correct first-time screen?
- Did they save an observing home?
- Did Tonight load?
- Did Polaris show an imaging recommendation or `Do Not Image`?
- Did the Yes/No usefulness response save?
- Did they return on another night?

## Ask before explaining

Ask these before coaching the tester or explaining the screen.

1. What did Polaris tell you to do tonight?
2. What do you think was the main reason?
3. What did you trust?
4. What did you doubt?
5. What felt missing, confusing, or too complicated?
6. Would you use Polaris before a real observing session? Why or why not?
7. Did the weather, Moon, darkness, and target window match what you expected
   locally?

## Watch for alpha-stop issues

Pause additional invitations if any answer here is yes.

- Did they see another user's data?
- Did sign-in or setup block them completely?
- Did Tonight repeatedly fail to load?
- Did they think Polaris controls the telescope or protects equipment?
- Did they rely on Polaris as a safety system?
- Did the recommendation look stale, simulated, or disconnected from the real
  night?

## Evidence to keep

- One short quote that captures the main reaction:
- Most confusing moment:
- Most valuable moment:
- Main reason they trusted or distrusted the recommendation:
- Any safe request ID:
- Screenshot received: yes / no

## Doug's decision

Choose one after the session.

- Keep inviting one tester at a time.
- Hold and fix onboarding.
- Hold and fix sign-in or load reliability.
- Hold and fix recommendation explanation.
- Park as feature request; no change yet.

One-sentence rationale:

## After the session

1. Paste the sanitized summary into the main Codex project task.
2. Update [`ALPHA_TESTER_FLIGHT_LOG.md`](ALPHA_TESTER_FLIGHT_LOG.md).
3. Run the aggregate metrics report before deciding whether to invite another
   tester:

       .venv/bin/python scripts/alpha_metrics_report.py --env-file .env.staging

4. Compare the metrics review focus with the flight log, then decide whether to
   keep going, hold for a fix, or park a request.
