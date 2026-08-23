# Version Map 

This repo is developed across sequential Arena sessions — one branch per
session. The auto-generated branch names are opaque, so **this file is the
human-readable version map. The highest version number is always the newest
work.**

> ## 🏆 LATEST: **v3**
> Branch: `arena/01a02bbc-arena-dim` · commit `eeaf6bb` · last updated 2026-08-23 00:44 UTC
> What it adds: Rhythm Interpretation Laboratory, modular accessible design
> system, enforced frontend feature boundaries, pending-CI documentation.

## Version table

| Ver | Branch | SHA | Last updated (UTC) | What's in it |
|-----|--------|-----|--------------------|--------------|
| v0 | `main` | `b51112c` | 2026-08-22 02:09 | Base: research prompt (`prompt.md`) only |
| v1 | `arena/01a02738-arena-dim` | `6068e72` | 2026-08-22 03:14 | Full app: analysis engine + FastAPI + React dashboard; backend serves built frontend; GitHub Actions test-deploy tunnel workflow |
| v2 | `arena/01a02969-arena-dim` | `dafb24a` | 2026-08-22 12:40 | + Tempo curve chart + estimated time-signature (meter) analysis (backend + frontend) |
| **v3** | `arena/01a02bbc-arena-dim` | `eeaf6bb` | 2026-08-23 00:44 | + Rhythm Interpretation Laboratory; dashboard refactored into modular accessible design system; feature boundaries; pending CI documented |

## Lineage

```
v0  main
 └─ v1  arena/01a02738-arena-dim
     ├─ v2  arena/01a02969-arena-dim   (tempo / meter line)
     └─ v3  arena/01a02bbc-arena-dim   (design-system line) ← LATEST
```

⚠️ **v2 and v3 are sibling branches** — v3 does **not** contain v2's
tempo-curve / meter work. Merging both lines will require resolving
frontend conflicts.

## Check the newest branch in 10 seconds

```bash
git fetch -q
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:relative) | %(refname:short) | %(objectname:short)' \
  refs/remotes/origin
```

Top line = newest branch.

## Conventions for future sessions

1. Every new session branch gets the next version number, appended to the table.
2. Keep the 🏆 **LATEST** pointer at the top up to date.
3. When a version is merged into `main`, record the merge commit in the table.

## Optional: give the branches friendly names yourself

Rename on GitHub (Settings → Branches → pencil icon) or locally:

```bash
git fetch
git push origin arena/01a02bbc-arena-dim:v3        # push under the new name
git push origin --delete arena/01a02bbc-arena-dim  # then delete the old name
```

Then update the table in this file to match.
