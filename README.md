# BuJo — ADHD-first Bullet Journal

A CLI + TUI bullet journal built for ADHD-C brains. No habit trackers, no
decorative spreads. Just capture, migrate, reflect. Data lives in plain
markdown files — fully Obsidian-compatible.

## Install

```bash
pip install bujo-cli
```

For development (editable install):

```bash
git clone https://github.com/naungmon/bujo-cli.git
cd bujo-cli
pip install -e .
```

## Quick Start

```
$ bujo

▸ _
```

Type directly. That's it. No menus, no buttons, no "press Enter to continue."

```
▸ t gotta call jackson          ← Enter →  · gotta call jackson
▸ e digital nomad club today    ← Enter →  ○ digital nomad club today
▸ feeling scattered             ← Enter →  – feeling scattered  (no prefix = note)
▸ finish the report!            ← Enter →  ★ finish the report
▸ done: wrote the tests         ← Enter →  × wrote the tests
▸ k that rebrand idea           ← Enter →  ~ that rebrand idea
▸ > follow up Tyson             ← Enter →  > follow up Tyson
```

The prefix sets the type. Everything after is the content. No prefix → note.

## How It Works

### Opening the app

**First time today (empty log):** The input bar is focused. Cursor blinks.
Start typing. The app already knows you're here to capture.

**Returning (entries exist):** The entry list is focused. Cursor lands on
the last entry. You can immediately arrow through and update things. The
input bar is still there — type anything to drop back into capture mode.

The app decides the starting state. Not you.

### Two modes

**Input mode** — `▸` in bright cyan. You're capturing. Type and Enter.
The `▸` prompt is your anchor. Everything else is dim.

**Nav mode** — `▸` dimmed. You're reviewing. Arrow through entries and
update them.

Press **Escape** to toggle between modes. That's the only key you need
to remember.

### Nav mode actions

| Key | Action |
|-----|--------|
| ↑ ↓ | Move through entries |
| `x` | Mark selected done |
| `k` | Kill selected |
| `>` | Migrate selected |
| `r` | Retype (edit entry text) |

### Prefix system

Works everywhere — the TUI input bar and the CLI `bujo capture` command.

| Prefix | Type | Example |
|--------|------|---------|
| `t` or `task` | Task | `t buy milk` |
| `n` or `note` | Note | `note feeling good` |
| `e` or `event` | Event | `event meeting at 3` |
| `*`, `priority`, or `p` | Priority | `* finish report` |
| `x` or `done` | Done | `done wrote tests` |
| `k` or `kill` | Killed | `k that idea` |
| `>` | Migrated | `> carry forward` |
| (no prefix) | Note | `feeling focused` |
| `!` at end | Priority | `finish report!` |
| `important` / `urgent` | Priority | `fix bug important` |

### Session detection

The app reads the room on launch:

- **Empty today** → input mode, cursor ready
- **Entries exist** → nav mode, cursor on last entry

Someone reopening bujo mid-day didn't open it to stare at a blinking cursor.
They came back to update what happened. The app knows that.

## TUI Screens

| Key | Screen | Purpose |
|-----|--------|---------|
| (launch) | DailyView | Main entry list, always-on input bar |
| `m` | MonthlyView | Monthly priorities (3-5 max) |
| `f` | FutureView | Parked items, not dead |
| `M` | MigrationScreen | Review pending tasks |
| `Ctrl+B` | Coach | Inline coaching (any key dismisses) |
| `?` | HelpScreen | Keybinding reference |

## CLI Commands

| Command | Description |
|---------|-------------|
| `bujo` | Launch TUI |
| `bujo add t\|n\|*\|e\|x\|k "text"` | Add entry (ASCII symbol) |
| `bujo capture "text"` | NLP auto-detect and add |
| `bujo log` | Print today's log |
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

## Coaching (Ctrl+B)

Press `Ctrl+B` from the DailyView to get inline coaching.

- **Fewer than 5 entries:** A gentle nudge to keep logging.
- **5+ entries:** Full analysis — momentum, streak, stuck tasks, kill
  themes, most productive time, and one coaching question.

No JSON output. No modal. No box. Just text in the list area. Any key closes.

## Time-Aware Greetings

The header adapts to your time of day and context:

- **Morning** (05:00–11:59): Energetic, forward-looking
- **Afternoon** (12:00–16:59): Grounded, progress-focused
- **Evening** (17:00–21:59): Wind-down, reflective
- **Late** (21:00–04:59): Calm, no pressure

Streaks are acknowledged when 3+ days. Mondays prompt priority-setting.
Fridays suggest migration before the weekend.

## Analytics

### `bujo coach` (JSON)

Returns structured data for AI integration:

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
pip install bujo-cli[hotkey]  # install keyboard dependency
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

## KiloCode / Cursor / Windsurf (manual)

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
| `EDITOR` / `VISUAL` | Editor for raw editing | notepad (Win) / nano |

## Contributing

This is a personal project but PRs are welcome if they:

1. Keep the ADHD focus — reduce friction, don't add complexity
2. Don't add habit trackers or elaborate spreads
3. Maintain plain markdown compatibility
4. Include tests if adding new logic

## License

MIT — see [LICENSE](LICENSE).
