# ICP territory skill

**A Claude Code skill that turns an unqualified CRM account list into
balanced rep territories a sales leader can edit.** It grades every account
against a plain-English ICP using the company's own website, enriches it
with Apollo, and builds territories from the real fits. Books are evened out
where the map allows, and a live planner lets a sales leader change
territories and reassign accounts. Every grade comes with its evidence.

Demo video: https://www.loom.com/share/1a4319de51ca473ebc393f5a135c41b5  
Live planner: https://vtderise-collab.github.io/apollo-icp-territory-skill/example/territory_map.html

## What it does for a GTM team

- **Sales leader:** an interactive planner. Drag the radius, turn marquee
  accounts on or off, reassign accounts by hand, and watch the books
  rebalance live. Their choices feed back into the official plan.
- **Rep:** a book of real fits, each with the sentence the grade rests on.
- **Enterprise team:** a handoff list of chain and large-company fits.
- **RevOps:** a hygiene audit with a proposed fix for every record problem,
  and a Needs Review queue with a reason on every account.

## Why I built it

I solved this in my current role. Leadership wanted territories rebuilt
around marquee accounts, with no way to grade accounts against our ICP or
map them. Here I rebuilt it from scratch on Apollo: your brief's data-hygiene
idea plus the "ICP to a prioritized list" half of account planning.

## Why it matters: what it saves and unlocks

- **Time.** Grading by hand takes about 50 seconds an account. At 50,000
  accounts (an example size), that's 700 hours. The skill runs unattended.
- **Rep focus.** In the example, 70 of 136 accounts were confirmed not
  worth a call.
- **Fairer territories.** Built on evidence, not an industry tag, and
  balanced. Fits no territory covers are flagged.

## How it works: architecture and data flow

| Step | What happens | Done by |
|---|---|---|
| 1. Enrich | Size, HQ and industry tag for each account | Script + Apollo API |
| 2. Evidence | Reads each company's own website | Script |
| 3. Grade | Fit, Needs Review or Unlikely against `icp.md`, with an exact quote | Claude. Code verifies the quote. |
| 4. Validate | Scores the grades against 30 hand labels and a fixed pass bar | Script |
| 5. Set up | Asks: by state, or around marquee accounts and a radius | The user decides |
| 6. Territories | Assigns fits by CRM location, balances books, keeps manager overrides | Script |
| 7. Hygiene | Lists every record problem with a proposed fix | Script |

**Systems touched:** a CRM export (CSV) in; Apollo's live API; company
websites; rep books, the planner and audit lists (CSV and HTML) out.

**Example run:** 136 accounts for Rackwell, a made-up gym equipment seller.
24 Fit, 70 Unlikely, 42 Needs Review. 87% against hand labels (26 of 27 on
readable sites).

## Discussion questions, in short

Full answers in the
[write-up](https://github.com/vtderise-collab/apollo-icp-territory-skill/blob/main/docs/WRITEUP.md).

- **[Assumptions](https://github.com/vtderise-collab/apollo-icp-territory-skill/blob/main/docs/WRITEUP.md#assumptions):**
  prospects live in the CRM (read here as a CSV export), the CRM location
  is the real site (Apollo returns headquarters), chains buy centrally, and
  the website is the most current truth.
- **[Design](https://github.com/vtderise-collab/apollo-icp-territory-skill/blob/main/docs/WRITEUP.md#why-a-skill-not-a-script-or-an-mcp-call):**
  a skill because the grade is a judgment and everything else is a script.
  Apollo is called by API from a script; Apollo data alone gives size and a
  tag, not a fit decision. Left out: ranked contacts and CRM write-back.
- **[Where I overrode AI](https://github.com/vtderise-collab/apollo-icp-territory-skill/blob/main/docs/WRITEUP.md#where-ai-helped-and-where-i-overrode-it):**
  it used Apollo's HQ location, trusted wrong-company matches, and built
  territories one fixed way. I required CRM locations, added a name check,
  and made the skill ask. Grading ran in a blind session.
- **[Production](https://github.com/vtderise-collab/apollo-icp-territory-skill/blob/main/docs/WRITEUP.md#what-i-would-harden-for-production):**
  a direct Salesforce connection (CLI or MCP) in place of the CSV export, a
  larger validation set, a headless browser, a scoped key, CRM write-back
  after manager approval.
- **[Rollout](https://github.com/vtderise-collab/apollo-icp-territory-skill/blob/main/docs/WRITEUP.md#rollout-and-success-plan):**
  pilot with half the mid-market reps, managers approve changes, track Fit
  conversion and referrals near marquee accounts.
