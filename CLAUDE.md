# BuJo — ADHD-first Bullet Journal

This project contains a personal bullet journal system adapted for ADHD.
When working in any session, Claude Code auto-reads this file.

## What this is

A CLI + TUI journal built on the Bullet Journal method, adapted for ADHD-C
(combined type, inattentive dominant). Data lives in `~/bujo-vault/` as plain
markdown files — fully Obsidian-compatible.

## Vault structure

```
~/bujo-vault/
  daily/          YYYY-MM-DD.md  — one file per day
  monthly/        YYYY-MM.md     — monthly priorities
  future/         future.md      — parked items, not dead
  reflections/    YYYY-MM-DD.md  — starred insights
```

## Symbol system

Files store ASCII. The TUI renders as Unicode.

| ASCII (in files) | Display (in TUI) | Meaning |
|------------------|------------------|---------|
| t | · | Task |
| x | × | Done |
| > | > | Migrated |
| k | ~ | Killed |
| n | – | Note |
| e | ○ | Event |
| * | ★ | Priority |

## Slash commands

- `/bujo` — Read logs, synthesize patterns, give coaching (runs `bujo coach`)

## Quick CLI

```bash
bujo                  # launch TUI
bujo add t "text"     # add task
bujo add n "text"     # add note
bujo add * "text"     # add priority
bujo add e "text"     # add event
bujo capture "text"   # NLP auto-detect (note: → n, ! → *, etc.)
bujo log              # print today
bujo summary          # raw log dump
bujo coach            # JSON for AI coaching
bujo coach --human    # readable coaching output
bujo insights         # analytics dashboard
bujo week             # weekly summary
bujo streak           # current streak
bujo template morning # apply template
bujo vault            # show vault path
```

## TUI screens

| Key | Screen | Purpose |
|-----|--------|---------|
| (launch) | DailyView | Main entry list, time-aware header |
| a | AddEntryScreen | Type-first input, auto-detects symbol |
| m | MonthlyView | Monthly priorities (3-5) |
| f | FutureView | Parked items |
| r | ReflectionView | Starred insights |
| M | MigrationScreen | Review pending tasks |
| i | InsightsView | Analytics dashboard |
| Q | QuickCaptureScreen | Same as AddEntryScreen |
| e | — | Open in $EDITOR |
| ? | HelpScreen | All keybindings |

## Coaching context

When `/bujo` is invoked, read `bujo coach --human` output and:

1. Synthesize patterns: what keeps getting avoided, killed, migrated
2. Note momentum (building/steady/stalling/stalled)
3. Reference stuck tasks by name if present
4. Note priority alignment and most productive time
5. End with exactly one question — not a list, one question

Tone: direct, honest, no fluff. Treat the user as someone who can handle truth.
