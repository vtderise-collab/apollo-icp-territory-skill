# Rackwell ICP (written policy)

Rackwell sells and services commercial gym equipment: treadmills, bikes,
rowers, strength machines, racks and free weights.

This file is the policy. The grader applies it and never invents it. Changes
to this file are made by the policy owner and recorded with the reason.

## The one rule

**A Fit runs a member-facing floor of cardio or strength machines.**

Members (or paying customers) walk in and use the machines themselves. Every
grade comes from that rule. The examples below show how it applies; they are
not separate rules.

## Fit: signals on the website

- Memberships, "join now", day passes, free trial pass, monthly rates
- An open gym, weight room, fitness floor, cardio area, 24/7 access
- Named equipment members use: treadmills, ellipticals, bikes, rowers,
  squat racks, cable machines, dumbbells, free weights, strength machines
- Photos or tour pages of a gym floor, "our facility", amenities lists

Examples that are Fit under the rule:
- Independent and regional gyms, health clubs, fitness centers, CrossFit
  boxes with a lifting floor, community or college fitness centers that sell
  memberships
- A location of a national chain (Planet Fitness, Anytime Fitness). Grade it
  Fit on the rule. Segment (Enterprise vs Mid-Market) is decided later by a
  script from Apollo data, not by the grader.
- A physical therapy clinic that also sells gym memberships
- A boxing or martial arts gym whose site shows a cardio or strength
  machine floor

## Unlikely: no member-facing machine floor

- Yoga, pilates, barre, dance and stretch studios
- Boxing and martial arts gyms with no machine floor (bags, rings, mats)
- Physical therapy, chiropractic and rehab clinics that do not sell gym
  memberships
- Spas, massage, wellness and beauty businesses
- Retail: sporting goods, apparel, supplements, nutrition stores
- Equipment makers, sellers and repair shops (competitors or channels)
- Fitness apps, online coaching, personal trainers with no facility
- Anything else that clearly has no machine floor (hockey clubs, schools
  without a member gym, restaurants)

## Mixed signals: judge density, not one word

- A gym that also sells supplements, apparel or an app is still Fit.
- A studio that mentions "strength" once in a class name is not a gym floor.
  It needs members using machines, not a class that uses kettlebells.
- One passing mention ("we partner with local gyms") does not make a Fit.
- If the homepage is mostly about one thing, that thing decides, unless a
  subpage clearly shows a member machine floor.

## Needs Review: only when the evidence cannot be seen clearly

Needs Review never means "policy undecided". Use it only with one of these
reasons:

| reason_code | When |
|---|---|
| `scrape_failed` | The pipeline could not read the site (no website, DNS, timeout, HTTP error) |
| `parked_or_empty` | Parked domain, for-sale page, or almost no text |
| `wrong_business` | The site is clearly about a different business than the account name |
| `cannot_tell` | Readable site, but nothing says whether members use a machine floor |
| `invalid_output` | Set by the checker, never by the grader: output did not parse or the quote was not found in the text |

## What the grader does not use

- Apollo's industry tag decides nothing. It is shown only so the grader can
  note when the website disagrees with it.
- Size, employee count and headquarters location. Segment is a separate step.
- Anything not in the evidence record. No outside knowledge of the business.
