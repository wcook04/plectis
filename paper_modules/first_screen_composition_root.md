# First-Screen Composition Root

`first_screen_composition_root` is the contract for the one screen a cold
reader should see before choosing a deeper Microcosm route.

## Purpose

Microcosm already has the important deeper surfaces: route maps, workingness,
authority ceilings, standards, receipts, source-open body imports, and the
localhost observatory. The first-screen problem is not lack of depth. It is
that depth lands poorly when the first encounter is a long command inventory
or a raw JSON payload.

The composition root says what has to fit on one screen:

1. One shared terminal selector: `microcosm hello <project>`.
2. One shared behavior proof: `microcosm tour --card <project>`.
3. Three reader branch handles after that shared card: safety/evals engineer,
   hiring reviewer, and peer developer.
4. Evidence counts framed as accounting, not maturity or progress scores.
5. A runnable-to-structural join: the folder-local command is one visible
   exercise of a larger source-open substrate.
6. An omission receipt: the card names the deeper route map, receipts,
   standards, workingness, authority, and observatory drilldowns instead of
   copying them.
7. An authority ceiling that rejects release, hosted publication, provider
   calls, source mutation, private-data equivalence, score-based progress, and
   whole-system correctness.

## Reader Branches

The shared first command comes before branching. Reader branches select the
next inspection surface; they do not create audience-specific authority.

| Reader | First branch | Evidence focus |
|---|---|---|
| Safety/evals engineer | `microcosm status --card <project>` plus authority and workingness drilldowns | Evidence classes, authority ceilings, body-copy boundaries, anti-claims, standards, and failure modes. |
| Hiring reviewer | legibility scorecard plus compact tour card | Is it real, local, bounded, and honest about what is not proven. |
| Peer developer | compact tour card plus project observation drilldown | Can a clone produce local `.microcosm/` state and inspect the route/work/event/evidence chain. |

## Reader Selection Card

The machine-readable selector lives at
`atlas/entry_packet.json::reader_first_screen_routes.reader_selection_card`.
It is the public first-screen handoff between terminal prose and branch-specific
drilldowns:

```bash
microcosm hello --reader safety_evals_engineer <project>
microcosm hello --reader hiring_reviewer <project>
microcosm hello --reader peer_developer <project>
```

Those focused projections are allowed to hide the other two branches, but not
the shared behavior proof, evidence-accounting frame, runnable-to-structural
join, omission receipt, or authority ceiling. The selector should therefore be
read as a branch router, not a personalized success claim.

## Validation Shape

The standard is intentionally a composition contract, not a runtime authority.
When a runtime card consumes it, validation should check that the card has a
single terminal selector, one shared behavior proof, the three reader route
ids, the reader-selection card ref, evidence-accounting context, a
runnable-to-structural join, omission receipts, and the authority ceiling.

## Public Card Emitter

`scripts/first_screen_composition_card.py` projects this contract into a
public-root JSON card:

```bash
python3 scripts/first_screen_composition_card.py --project-label <project>
```

It can also emit the terminal-sized first screen directly:

```bash
python3 scripts/first_screen_composition_card.py --project-label <project> --format text
```

The text projection can focus one reader branch while preserving the same
shared first command, evidence-count frame, omission receipt, and authority
ceiling:

```bash
python3 scripts/first_screen_composition_card.py --project-label <project> --format text --reader safety_evals_engineer
```

`--reader all` remains the default. Focused reader projections are presentation
routes only: they reduce the first-screen branch set, but they do not create a
different claim frame or audience-specific authority.

The emitter is intentionally narrow. It does not import private runtime state
or source bodies. It loads this standard, emits the one shared command and
three branch handles, frames evidence counts as accounting, names the
runnable-to-structural join, and carries the standard's omission receipt and
authority ceiling.

## Authority Ceiling

This module does not replace the cold-reader route map, standards-control lens,
workingness map, public reveal walkthrough, or observatory. It only governs the
compression boundary that lets those deeper surfaces land in the right order.
