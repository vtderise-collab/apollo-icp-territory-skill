# ICP territory skill

**A Claude Code skill that turns an unqualified CRM account list into rep
territories.** It grades every account against a plain-English ICP using the
company's own website, enriches it with Apollo, and assigns the real fits to
reps. Every grade comes with its evidence.

## What it does for a GTM team

- **Sales leader:** a territory map and summary, with coverage gaps called
  out, to approve the plan.
- **Rep:** a book of real fits, each with the sentence the grade rests on.
- **Enterprise team:** a handoff list of chain and large-company fits.
- **RevOps:** a data-hygiene audit with a proposed fix for every record
  problem, plus a Needs Review queue with a reason on every account.

## Why it matters

- **Time.** Grading takes about 50 seconds per account by hand. At 50,000
  accounts (an example size), that is about 700 hours of one person's work.
  The skill runs unattended, at least five times faster, with a checkable
  quote on every grade.
- **Rep focus.** Reps stop calling accounts that will never buy. In the
  example, 70 of 136 accounts were confirmed not worth a call.
- **Better, fairer territories.** Carves are built on evidence, not an
  industry tag, and books are balanced so each rep gets about the same
  number of fits. The example also flagged fits that no territory covers,
  and moved 7 chains to
  enterprise.

## How it works: architecture and data flow

```
 CRM export (CSV) ──► 1 Enrich ◄── Apollo API (size, HQ, industry tag)
                      2 Evidence ◄── company websites (read directly)
                      3 Grade      Claude + references/icp.md, quote verified by code
                      4 Validate   hand labels, fixed pass bar
                      5 Set up     asks the user: by state, or around marquee accounts
                      6 Territories CRM locations only
                      7 Hygiene    record problems, each with a proposed fix
                         ▼
            rep books · map · Enterprise list · Needs Review · hygiene audit (CSV, HTML)
```

- **Systems it touches:**
  - Apollo (live API).
  - Company websites.
  - The CRM export (CSV).
  - CSV and HTML outputs.
  - Claude Code runs the skill.
- **Territories, your way:** the skill asks how to build them. By state
  is the simplest. Around marquee accounts, it balances the books and shows
  coverage gaps: fits that no territory covers.
- **Division of labor:** scripts do all data work. The model makes one
  judgment per account and never edits the policy. The policy is one
  sentence the business owns: "A Fit runs a member-facing floor of cardio or
  strength machines."

## Proof: example run

The example is Rackwell, a made-up gym equipment seller with 136 CRM
accounts across Illinois, Wisconsin and Indiana.
- **Fits:** 24 found. 12 placed in three balanced marquee territories
  (6, 4, 2), with one book flagged as unable to balance. 7 went to the
  enterprise team, and 42 were flagged for review.
- **Hygiene audit:** 164 record problems on 105 accounts, each with a fix.
  Apollo matched 88 trusted, 34 had no record, and 9 were name mismatches.
- **Validation:** 87% against a 90% bar, and 26 of 27 on the sites it could
  read. Three of the four misses were sites that blocked the scraper.

## Why I built it

I solved this problem in my current role. Leadership wanted territories
rebuilt around marquee accounts, with no way to grade or map accounts. Here I
rebuilt it from scratch on Apollo. Apollo's size and headquarters data splits
regional accounts from enterprise ones, and the skill audits that data
instead of trusting it. No code or data from the original build is in this
repo.

## Rollout

- **Pilot:** half the mid-market reps work from it for a quarter. The other
  half are the comparison.
- **Managers approve:** the plan, ownership changes and holdover requests.
- **Target measures:**
  - Fit conversion above the rest of the book.
  - Pipeline per territory.
  - Referrals near marquee accounts.
  - Live grades stay at 90% or better.

## Design and trust

- **Why a skill:** the judgment needs a model, the rest needs code, and the
  policy must be a file a sales leader can read.
- **Where I overrode the AI:**
  - CRM locations over Apollo headquarters.
  - Needs Review only for "could not see".
  - A guard against wrong Apollo matches.
  - Blind grading.
- **Before reps depend on it:**
  - A larger validation set.
  - A headless browser for JavaScript sites.
  - Image evidence.
  - A scoped key.
  - CRM write-back after approval.
