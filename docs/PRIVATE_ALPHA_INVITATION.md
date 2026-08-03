# Project Polaris: first private-alpha invitation

Status: ready for Doug to personalize and send  
Audience: one trusted smart-telescope user at a time

## Before you send it

1. Tester support for this first trusted cohort goes to
   `drogers08121@gmail.com`.
2. Create the tester's invitation in Supabase. Do not share an account,
   password, or invitation link with more than one person.
3. Send the message below privately. Do not post it to a Facebook group.
4. Record the invitation date in the private-alpha test plan or Doug's own
   tracker. Do not record passwords, tokens, or street addresses.

## Ready-to-send message

> Hi <FIRST NAME>,
>
> I'm testing an early private version of Project Polaris, a planning helper
> for smart-telescope users. It looks at your observing location, weather,
> darkness, Moon conditions, and target visibility, then gives a plain-English
> suggestion for tonight. It does **not** control your telescope and it is not
> an equipment-safety system.
>
> I’m inviting only a few people who are comfortable trying unfinished
> software. If you are interested, I’ll send a private account invitation.
>
> The test is simple: set up one observing location, read the nightly
> recommendation, tell me in your own words what it is suggesting and why, and
> return for one more real observing decision on a later night. Please tell me
> what is confusing or unhelpful—honest feedback is more useful than being nice.
>
> Polaris stores the account and observing-location information needed to make
> the recommendation. You may use approximate coordinates instead of your exact
> observing address. Please do not rely on Polaris as the sole basis for
> protecting equipment or deciding whether it is safe to open an observatory.
>
> If you'd like to take part, reply here. For a problem or question during the
> test, contact me at drogers08121@gmail.com and include a screenshot or the small
> request ID shown in an error message if there is one.
>
> Thanks—Doug

## Tester worksheet

Ask these questions after the tester completes the first visit. Do not coach
the answer before they respond.

1. In your own words, what did Polaris recommend for tonight?
2. Why do you think it made that recommendation?
3. Was there anything you were unsure how to read or act on?
4. Would you use this information to decide what to image tonight? Why or why
   not?
5. What information did you expect but not find?
6. Please return on a different night and repeat the process. Did anything feel
   easier or harder the second time?

## Onboarding retest script

Use this only for a targeted retest after an onboarding change. The goal is to
observe confusion, not to teach the screen.

Before they open the link:

> I’m going to watch where Polaris is clear or confusing. Please say out loud
> what you think each screen wants you to do. I won’t explain anything unless
> you get completely stuck.

While they are on setup, record:

- Did they understand what an observing home is?
- Did they choose **Fill this in for me** without prompting?
- If they saw latitude/longitude, did those fields confuse or stop them?
- Did they understand that Polaris does not need a street address?
- After saving, did **You're ready for tonight** make the next step clear?

After they click **Show tonight's plan**, ask:

> In your own words, what did Polaris just save, and what is it using that
> information for?

Passing result: the tester reaches the first Tonight plan without live help and
understands that Polaris saved an approximate observing location for planning.
If they still get stuck on coordinates, use
[`ONBOARDING_LOCATION_ENTRY.md`](ONBOARDING_LOCATION_ENTRY.md) as the next
implementation path.

## Ready-to-send first-use check-in

Send this after a tester has had a chance to open Polaris and look at a real
Tonight recommendation. Do not send it immediately after the invitation; give
them room to explore without coaching.

> Hi <FIRST NAME> — thanks again for trying Polaris. When you have a minute,
> could you answer these in your own words? Short answers are perfect, and
> blunt honesty helps me much more than being polite.
>
> 1. What did Polaris tell you to do tonight?
> 2. What do you think was the main reason it gave that advice?
> 3. Was anything unclear, missing, or more complicated than it needed to be?
> 4. Would you use Polaris again before a real observing session? Why or why
>    not?
>
> If you hit a problem, a screenshot is very helpful. Please do not send a
> password or your exact home address. Thank you — Doug

### When to use the answer

- Record their answer in `ALPHA_TESTER_FLIGHT_LOG.md` using a tester alias.
- Use `ALPHA_FEEDBACK_CAPTURE_SHEET.md` if you are taking notes during a live
  or near-live tester conversation.
- A wrong explanation of the recommendation is a comprehension issue, even if
  the page technically worked.
- A feature request becomes a roadmap candidate only when it supports the
  nightly decision or repeats across testers.

## Quick response templates

Use these as private one-to-one replies. Keep the tone personal; do not paste
account links into a public thread.

### If they say yes

> Thank you — I really appreciate it. I’ll send a private account invitation.
> Please use an approximate observing location if you prefer, and do not send me
> a password or exact address. The most helpful feedback is whether the
> recommendation made sense, whether you trusted the reason, and what felt
> wrong or missing.

After sending the Supabase invitation, add:

> The invite should let you choose your own password. After setup, Polaris will
> show one Tonight recommendation. It may say **Do Not Image** if conditions are
> poor; that is still a useful test if the reason is clear.

### If they ask what it does

> Polaris is a small planning helper for smart-telescope users. It looks at your
> approximate observing location, weather, darkness, Moon, and target visibility
> and gives a plain-English recommendation for tonight. It does not control your
> telescope and it is not a safety system. I’m testing whether the
> recommendation is clear and trustworthy enough to be useful before an imaging
> session.

### If they are busy

> No problem at all. I’m keeping this intentionally small, so there is no rush.
> If you have time later, I’d still value your honest take. If not, I appreciate
> you considering it.

### If they report a bug or failed load

> Thank you — that is exactly the kind of thing I need to catch. What page were
> you on, what were you trying to do, and what happened instead? If Polaris
> showed a request ID, please send just that ID and a screenshot if convenient.
> Please do not send a password, sign-in link, access token, or exact observing
> address.

### If the recommendation seems wrong

> That is very useful feedback. Before I explain anything, could you tell me
> what felt wrong: the target choice, timing, weather, Moon, local horizon/trees,
> telescope settings, or something else? I’m trying to learn whether Polaris is
> missing information or whether the explanation is not earning trust.

## What Doug records

- Tester alias or first name only.
- Invitation date and whether the invitation was accepted.
- Setup: completed alone, completed with help, or abandoned.
- Whether the tester accurately explained the recommendation.
- Whether they made a real observing decision with Polaris.
- Second-visit date, most valuable part, biggest confusion, and any reported
  issue's request ID.
- Whether they would miss Polaris if it went away.

## Stop and contact the tester

Immediately pause further invitations if the tester reports another person’s
data, a misleading safety claim, a recommendation presented as live when it is
not, or an error that blocks setup or planning. Preserve only the safe request
ID and a screenshot; never ask for a password, access token, or exact address.
