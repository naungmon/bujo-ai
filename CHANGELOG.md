# Changelog

## v3.0.0 — 2026-03-16

### Added
- Time-aware session greetings with streak and pending awareness (`session_greeting()`)
- `bujo week` command for weekly summary
- `bujo coach --human` human-readable coaching output
- `most_productive_time()` analytics
- `tasks_per_day_avg()` analytics
- Git-ready packaging (LICENSE, .gitignore, PyPI metadata)
- `bujo[hotkey]` optional dependency for global hotkey

### Fixed
- CLAUDE.md synced to v2.1+ symbol system
- README rewritten for public audience (15 sections)
- Slash commands updated to use `bujo coach --human`
- `.kilocode/commands/bujo.md` updated with Windsurf/Cursor note

### Changed
- Package name: `bujo` → `bujo-journal`
- Version: 2.0.0 → 3.0.0

---

## v2.1.0

### Changed
- File format: ASCII symbols (t x > k n e *) instead of Unicode
- Input model: type-first with `a` key, auto-detect symbol
- In-place retype: press symbol key on selected entry to change type

## v2.0.0

### Added
- Analytics engine (`InsightsEngine`)
- NLP-lite capture (`note:`, `event:`, `done:`, `!`, `important`)
- Time-aware greetings
- Obsidian frontmatter integration (opt-in)
- Dashboard generation (opt-in)
- Global hotkey `Win+Shift+B` via `bujo-capture`

## v1.0.0

### Added
- Basic TUI with DailyView, MonthlyView, FutureView, Reflections, Migration
- CLI with add, log, summary, vault
- Claude Code `/bujo` slash command
- Plain markdown vault (Obsidian-compatible)
