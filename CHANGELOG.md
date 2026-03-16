# Changelog

## v1.0.0 — 2026-03-16

### TUI — Input-First Interaction Model
- Always-on input bar with `▸` prompt at bottom of screen
- Session detection: empty today → input mode, entries exist → nav mode
- Navigation mode: Escape toggle, ↑↓ movement, x/k/>/r actions
- Prompt color indicator: bright cyan in input mode, dim in nav mode
- Inline coach (Ctrl+B): deflect <5 entries, insights ≥5, no modals
- First-run experience: prefix guide shown once on clean vault
- Zero borders anywhere — clean notepad feel

### Prefix Parsing (TUI + CLI)
- `t` or `task` → task, `n` or `note` → note, `e` or `event` → event
- `*`, `priority`, or `p` → priority, `x` or `done` → done
- `k` or `kill` → killed, `>` → migrated
- `!` suffix or `important`/`urgent` keywords → priority
- No prefix → note (default)

### CLI
- `bujo` — launch TUI
- `bujo add t|n|*|e|x|k "text"` — add entry
- `bujo capture "text"` — NLP auto-detect
- `bujo log` / `bujo coach` / `bujo coach --human` / `bujo insights`
- `bujo week` / `bujo streak` / `bujo template` / `bujo vault`

### Analytics & Coaching
- InsightsEngine: momentum, kill themes, stuck tasks, priority alignment
- Weekly summary with totals and insights
- Most productive time of day, average tasks per day
- Coaching nudge: one question at the end

### Time-Aware Session Greetings
- Morning/Afternoon/Evening/Late with context-aware messages
- Streak acknowledgement (3+ days)
- Monday priority prompt, Friday migration prompt

### Integration
- Obsidian frontmatter and dashboard (opt-in)
- Claude Code `/bujo` slash command
- KiloCode slash command
- Cursor/Windsurf integration guide
- Global hotkey `Win+Shift+B` (`pip install bujo-cli[hotkey]`)

### Architecture
- ASCII file format (t, x, >, k, n, e, *) with Unicode rendering
- Legacy Unicode backward compatibility
- 155 tests covering models, analytics, capture, time, CLI, integrations
- pyproject.toml with `bujo-cli` package name
