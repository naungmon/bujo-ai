# BuJo — ADHD-first Bullet Journal

A CLI + TUI bullet journal built for ADHD-C brains. No habit trackers, no
decorative spreads. Just capture, migrate, reflect. Data lives in plain
markdown files — fully Obsidian-compatible.

## Install

```bash
pip install bujo-journal
```

For development (editable install):

```bash
git clone https://github.com/naungmon/bujo-cli.git
cd bujo-cli
pip install -e .
```

## Quick Start (60 seconds)

```bash
bujo add t "buy milk"          # add a task
bujo add n "feeling focused"   # add a note
bujo add "*" "finish report"   # add a priority
bujo log                        # see today's entries
bujo                            # launch the TUI
```

## TUI Screens

| Key | Screen | Purpose |
|-----|--------|---------|
| — | DailyView | Main entry list with time-aware header |
| `a` | AddEntryScreen | Type-first input, auto-detects symbol |
| `m` | MonthlyView | Monthly priorities (3-5 max) |
| `f` | FutureView | Parked items, not dead |
| `r` | ReflectionView | Starred insights worth keeping |
| `M` | MigrationScreen | Review and decide on pending tasks |
| `i` | InsightsView | Analytics dashboard |
| `Q` | QuickCaptureScreen | Fast capture from anywhere |
| `e` | — | Open today's file in `$EDITOR` |
| `?` | HelpScreen | All keybindings |

## CLI Commands

| Command | Description |
|---------|-------------|
| `bujo` | Launch TUI |
| `bujo add t\|n\|*\|e\|x\|k "text"` | Add entry (ASCII symbol) |
| `bujo capture "text"` | NLP auto-detect and add |
| `bujo log` | Print today's log |
| `bujo summary` | Raw log dump |
| `bujo coach` | JSON for AI coaching |
| `bujo coach --human` | Readable coaching output |
| `bujo insights` | Analytics dashboard |
| `bujo week` | Weekly summary |
| `bujo streak` | Current streak count |
| `bujo template morning` | Apply template |
| `bujo vault` | Print vault path |

## Symbol System

Files store ASCII. The TUI renders as Unicode.

| ASCII | Display | Meaning |
|-------|---------|---------|
| `t` | · | Task |
| `x` | × | Done |
| `>` | > | Migrated |
| `k` | ~ | Killed |
| `n` | – | Note |
| `e` | ○ | Event |
| `*` | ★ | Priority |

## NLP Capture

The `bujo capture` command detects the symbol from your text:

| Input | Result |
|-------|--------|
| `bujo capture "buy milk"` | · task |
| `bujo capture "note: feeling good"` | – note |
| `bujo capture "event: meeting at 3pm"` | ○ event |
| `bujo capture "standup tomorrow"` | · task |
| `bujo capture "finish the report!"` | ★ priority |
| `bujo capture "done: wrote tests"` | × done |
| `bujo capture "fix bug important"` | ★ priority |

## Time-Aware Greetings

The TUI header adapts to your time of day and context:

- **Morning** (05:00–11:59): Energetic, forward-looking
- **Afternoon** (12:00–16:59): Grounded, progress-focused
- **Evening** (17:00–21:59): Wind-down, reflective
- **Late** (21:00–04:59): Calm, no pressure

Streaks are acknowledged when 3+ days. Mondays prompt priority-setting.
Fridays suggest migration before the weekend.

## Analytics

### `bujo insights`

Shows momentum (building/steady/stalling/stalled), streak, completion rate,
priority alignment, stuck tasks, and kill patterns.

### `bujo coach`

Returns structured JSON with:
- Stuck tasks (migrated 3+ times)
- Kill themes (what categories get dropped)
- Momentum score
- Priority alignment
- Most productive time of day
- Average tasks per day

### `bujo coach --human`

Readable formatted output with all the above, ending with one coaching question.

### `bujo week`

Weekly summary: totals for logged/done/killed/migrated, streak, most
productive time, and top insight.

## Global Hotkey

Capture entries from anywhere with `Win+Shift+B`:

```bash
pip install bujo-journal[hotkey]  # install keyboard dependency
bujo-capture              # start hotkey listener
```

Press `Win+Shift+B` (or `Ctrl+Shift+B` as fallback), type, Enter saves.

## Obsidian Integration

Set environment variables to enable Obsidian-specific features:

```bash
# Add YAML frontmatter to daily files
export BUJO_OBSIDIAN_FRONTMATTER=1

# Generate vault/dashboard.md with stats
export BUJO_DASHBOARD=1
```

Both are opt-in. BuJo writes standard markdown that Obsidian reads natively.

## Claude Code Integration

Copy `.claude/` to your home directory:

```bash
cp -r .claude ~/
```

In any Claude Code session, type `/bujo` to get a coaching synthesis based on
your logs. Claude runs `bujo coach`, analyzes patterns, and asks one honest
question.

## KiloCode / Cursor / Windsurf Integration

Copy `.kilocode/` to your home directory:

```bash
cp -r .kilocode ~/
```

For Windsurf or Cursor, add the contents of `.kilocode/commands/bujo.md` to
your system prompt or `.cursorrules`.

## Vault Structure

All data lives in `~/bujo-vault/` by default:

```
~/bujo-vault/
  daily/         YYYY-MM-DD.md
  monthly/       YYYY-MM.md
  future/        future.md
  reflections/   YYYY-MM-DD.md
  templates/     morning.md, evening.md, weekly.md
```

Override with the `BUJO_VAULT` environment variable:

```bash
export BUJO_VAULT=/path/to/your/obsidian/vault/bujo
```

## Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `BUJO_VAULT` | Vault location | `~/bujo-vault/` |
| `BUJO_OBSIDIAN_FRONTMATTER` | Add YAML frontmatter | off |
| `BUJO_DASHBOARD` | Generate dashboard.md | off |
| `EDITOR` / `VISUAL` | Editor for `e` key | notepad (Win) / nano |

## Contributing

This is a personal project but PRs are welcome if they:

1. Keep the ADHD focus — reduce friction, don't add complexity
2. Don't add habit trackers or elaborate spreads
3. Maintain plain markdown compatibility
4. Include tests if adding new logic

## License

MIT — see [LICENSE](LICENSE).
