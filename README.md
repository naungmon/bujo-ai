# BuJo — ADHD-first Bullet Journal

A CLI + TUI bullet journal built for ADHD-C brains. No habit trackers, no
decorative spreads. Just capture, migrate, reflect. Data lives in plain
markdown files — fully Obsidian-compatible.

## bujo-ai

This fork adds AI-powered dump capture. Type freely in one paragraph —
AI parses it into structured BuJo entries automatically.

### Requires

An OpenRouter API key. Get one at openrouter.ai/keys

### Setup (Windows)

```
$env:BUJO_AI_KEY="sk-or-your-key-here"
```

### Setup (Mac/Linux)

```
export BUJO_AI_KEY=sk-or-your-key-here
```

Default model: minimax/minimax-m2.7
Override: set BUJO_AI_MODEL to any OpenRouter model string.

### Usage

```
bujo dump "need to call jackson, feeling scattered, club tonight"
bujo dump          ← multiline mode
bujo dump --retry  ← re-parse saved drafts
```

Type freely in the main input — AI parses everything.

## Install

```bash
pip install bujo-ai
```

For development (editable install):

```bash
git clone https://github.com/naungmon/bujo-ai.git
cd bujo-ai
pip install -e .
```

## Quick Start

**First launch:** a prefix guide appears. Press any key for a 2-minute tour, or Escape to skip. Replay anytime with `bujo tutorial`.

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

Press **Escape** to cancel an inline edit and return to capture mode.
When not editing, Escape focuses the input bar so you can immediately type.

### Nav mode actions

| Key | Action |
|-----|--------|
| ↑ ↓ | Move through entries |
| `x` | Mark selected done |
| `k` | Kill selected |
| `>` | Migrate selected |
| `Ctrl+Z` | Undo last change |
| `Ctrl+Delete` | Clear all entries today |

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
| `Shift+M` | MigrationScreen | Review pending tasks |
| `Shift+R` | ReviewView | Monthly 6-perspective review |
| `Ctrl+B` | Coach | Inline coaching (any key dismisses) |
| `/` | SearchView | Full vault search |
| `?` | HelpScreen | Keybinding reference |

## CLI Commands

| Command | Description |
|---------|-------------|
| `bujo` | Launch TUI |
| `bujo tutorial` | Step-by-step walkthrough |
| `bujo add t\|n\|*\|e\|x\|k "text"` | Add entry (ASCII symbol) |
| `bujo capture "text"` | NLP auto-detect and add |
| `bujo dump "text"` | AI parse dump and save |
| `bujo dump` | Multiline dump mode |
| `bujo dump --retry` | Re-parse saved drafts |
| `bujo log` | Print today's log |
| `bujo summary` | Print 7-day logs summary |
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
| `<` | ← | Scheduled |
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
pip install bujo-ai[hotkey]  # install keyboard dependency
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

## Vault Structure

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
| `BUJO_AI_KEY` | OpenRouter API key | _(none — required for AI features)_ |
| `OPENROUTER_API_KEY` | OpenRouter key (fallback) | _(none)_ |
| `BUJO_AI_MODEL` | OpenRouter model | `minimax/minimax-m2.7` |
| `BUJO_OBSIDIAN_FRONTMATTER` | Add YAML frontmatter | off |
| `BUJO_DASHBOARD` | Generate dashboard.md | off |
| `BUJO_DEBUG` | Write AI debug log to vault | off |
| `EDITOR` / `VISUAL` | Editor for raw editing | notepad (Win) / nano |

## Contributing

This is a personal project but PRs are welcome if they:

1. Keep the ADHD focus — reduce friction, don't add complexity
2. Don't add habit trackers or elaborate spreads
3. Maintain plain markdown compatibility
4. Include tests if adding new logic

## License

MIT — see [LICENSE](LICENSE).
