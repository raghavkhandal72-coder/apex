# Show HN Launch Draft

## Title (pick one, under 80 chars):
- `Show HN: Apex – zero-dependency Python program repair in one 380 KB file`
- `Show HN: Apex – localize a bug, search for a one-token fix, check it on hidden tests`

**URL**: https://github.com/YOUR_USER/apex

---

## First comment (post it yourself immediately after submitting):

> Hi HN. I built Apex because I wanted a repair tool I could drop onto any machine with Python (air-gapped box, CI container) with no pip install and no API key.
>
> How it works: Ochiai spectrum-based fault localization points at suspicious lines, a bounded search over a small AST mutation grammar proposes fixes, and a counterexample loop (plus differential probes against a reference implementation when you have one) rejects candidates that only satisfy your visible tests.
>
> I'm trying to be upfront about limits:
> - It's bounded search, not formal verification. It handles operator/boundary/constant bugs, not new algorithms.
> - On QuixBugs (3 visible tests, rest hidden) it repairs 1 of 26 attempted; 1 overfit (`find_in_sorted`). Table and runner are in the repo.
> - Localization misses "loop exits one step early" bugs (it points at the symptom). Documented under Known Limitations.
> - Candidate code runs in an isolated subprocess, which is not a security sandbox.
>
> There's also an optional multi-model "council" mode that needs API keys; without keys it runs in a clearly labeled offline simulation and simulated models are never ranked.
>
> I'd love to hear which bugs it fails on. The "Apex can't fix my bug" issue template is for exactly that.

---

## Rules for Launch Day
- **Posting window:** Post Tue–Thu, ~8–9 AM US Eastern.
- **Fair play:** Don't ask anyone to upvote; don't use voting rings or bots.
- **Engagement:** Reply to every comment in the first 2 hours. Concede valid criticism plainly and open an issue for it.
- **Integrity:** Don't edit the README to hide a limitation someone found; document it instead.
- **Release tag freeze:** Never move a release tag after posting.
