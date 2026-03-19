# BuJo-AI Notepad Redesign — Design Spec

**Date:** 2026-03-17
**Status:** Reviewed
**Goal:** Make bujo-ai as easy as a notepad for average (non-technical) users while preserving full editability.

---

## Problem Statement

bujo-ai is a power-user tool. It requires users to learn a prefix system, two modes (input/nav), 7+ keybindings, 6 TUI screens, and 12 CLI commands. The AI-powered smart parsing already bridges "just type" to "structured journal," but the TUI interaction model still assumes the user knows how modes and prefixes work.

The goal is to make the TUI feel like opening a notepad — cursor ready, type anything, everything just works — while keeping entries fully editable and the power-user features accessible for those who find them.

## Target User

Anyone who journals. They want to open something, type, and close it. Structure happens behind the scenes. They should never need to read a README to use the app.

## Design Principles

1. **Typing is the default and only required action.** No modes to learn, no prefixes required.
2. **Every entry is editable text.** A journal you can't freely edit isn't a journal.
3. **The AI is the bridge.** It classifies entries so the user doesn't have to.
4. **Teach by doing, not by showing.** Progressive hints, not a manual.
5. **Power-user features are accessible, not required.** Prefixes, keybindings, and screens remain for those who discover them.

---

## Section 1: Core Interaction Model

### Launch Behavior

The app always launches with the cursor blinking in the input area. No mode detection. Capturing is the default action regardless of whether entries exist.

The current behavior (entries exist -> nav mode) is removed. Rationale: you open a notepad and the cursor is ready. Always.

### Input Flow

1. Type anything, press Enter -> saved.
2. If no prefix detected, AI classifies it (task, note, event, priority).
3. If prefix present (t, e, *, etc.), use it directly via `parse_quick_input` — skips AI call.
4. Fallback if AI unavailable: save as note.

**Note on prefix defaults:** `capture.py`'s `parse_quick_input` defaults no-prefix text to task (`t`). This only applies when an explicit prefix is detected but the text is otherwise empty — it does not conflict with the TUI flow. In the TUI, `smart_parse` in `ai_capture.py` is the sole input handler: it sends non-prefixed text to AI, and falls back to note (`n`) if AI is unavailable. `parse_quick_input` is only called when `has_explicit_prefix` returns true. CLI commands (`bujo capture`, `bujo add`) continue to use `parse_quick_input` directly.

**Input classification decision flow:**

```
User types text, presses Enter
  |
  v
has_explicit_prefix(text)?
  |-- YES --> parse_quick_input(text) --> (symbol, cleaned) --> append_entry
  |-- NO  --> ai_parse_dump(text)
                |-- API success --> [(symbol, text), ...] --> append_entry (each)
                |-- API failure --> fallback: ("n", text) --> append_entry
```

This flow should be documented as a code comment at the top of `smart_parse` in `ai_capture.py`, linking back to this spec section.

### Navigation (No Modes)

There is no explicit input/nav mode toggle. Instead:

- **Arrow up** from the input area moves focus into the entry list. The user is now browsing entries.
- **Arrow down** from the bottom of the entry list (or pressing Escape) returns focus to the input area.
- This is the same mental model as a text editor: arrow keys move you around. No mode to remember.

**Implementation detail — TextArea arrow-up handling:** The main input is a Textual `TextArea` widget, which consumes arrow key events for internal cursor movement. To enable focus transfer: subclass `TextArea` and override `key_up`. When the cursor is on the first line (or the TextArea is empty), arrow-up should call `self.screen.query_one("#entry-list").focus()` instead of moving the cursor. When the cursor is on any other line, let the default TextArea behavior handle it.

### Inline Editing

- Select an entry in the list, press **Enter** -> the entry text becomes an editable field in place.
- Edit the text, press **Enter** -> saved.
- Press **Escape** -> cancel edit, revert to original text.
- No "retype" migration flow. Just edit the text directly.
- The old `r` keybinding for retype is removed. Enter replaces it entirely.

**Implementation detail — inline edit widget:** When Enter is pressed on a highlighted entry, mount a single-line `Input` widget inside the `ListItem`, replacing the `Static` display. Pre-fill it with the entry text. The `Input.Submitted` event saves the edit. Escape removes the `Input` and restores the `Static`. Only one entry can be in edit mode at a time.

**Enter key disambiguation:** Enter has three contexts, resolved by focus:
1. **Main input TextArea has focus** -> submit new entry (current behavior).
2. **Entry list has focus, no inline edit active** -> start inline edit on highlighted entry.
3. **Inline edit Input has focus** -> save the edit.

These never conflict because only one widget has focus at a time. The priority Enter binding in DailyView checks which widget has focus and dispatches accordingly.

**Accidental Enter while navigating:** The entry list highlight is the only visual cue that Enter will start editing. This is consistent with how file managers and list UIs work (Enter = open/edit the selected item). The inline edit is lightweight and reversible — Escape cancels instantly with no side effects — so an accidental Enter is a low-cost mistake. No additional affordance (e.g., "press Enter to edit" tooltip) is needed; the highlight is sufficient.

### Status Changes

When an entry is highlighted in the list:
- `x` marks it done
- `k` kills it
- `>` migrates it

These are single-key shortcuts. The user never needs to learn them — they're discoverable through progressive hints and the help screen. Status change keys are only active when the entry list has focus and no inline edit is active.

### Undo

- **Ctrl+Z** reverses the last action (add, edit, mark done, kill, migrate).
- Undo stack is session-scoped (clears on app close).
- Supports multiple levels of undo within the session.
- **Known limitation:** undo does not persist across sessions. If the user edits an entry, closes the app, and reopens, that edit cannot be undone. This is acceptable for v1 — the markdown files are always human-editable as a fallback. Persistent undo (e.g., via an undo log file) can be added later if users request it.

**Undo action record structure:**

```python
@dataclass
class UndoAction:
    action_type: str        # "add", "edit", "status_change"
    file_path: Path         # which markdown file was modified
    original_line: str      # the line content before the action (empty string for "add")
    new_line: str           # the line content after the action
    description: str        # human-readable label, e.g. 'mark done "call Jackson"'
```

Undo for each action type:
- **add:** remove `new_line` from the file.
- **edit:** replace `new_line` with `original_line` in the file.
- **status_change** (done/kill/migrate): replace `new_line` with `original_line` in the file.

The `UndoStack` is a simple `list[UndoAction]` with `push()` and `pop()` methods, owned by `DailyView`.

---

## Section 2: Discoverability — Progressive Disclosure

### First Launch (Clean Vault)

The screen shows:
- Date
- Subtle greeting
- Input area with placeholder text: `just type anything...`

No prefix guide. No feature list. No welcome message.

### Empty States

All empty states look the same regardless of context:
- **First launch (no vault):** date, greeting, input with placeholder `just type anything...`, dim hint `no entries yet` in the list area.
- **Today with no entries:** identical to above — date, greeting, placeholder, `no entries yet`.
- **Browsing a past day with no entries:** date ribbon shows the past day, `no entries on this day` in the list area, input still active (saves to today, with the `viewing Mar 16 · typing saves to today` indicator visible).

### Milestone Hints (Shown Once Each)

| Trigger | Hint |
|---------|------|
| After first entry saved | `tip: start with "t" for task, "e" for event, or just type naturally` |
| After 3 entries | `tip: use arrow keys to browse your entries` |
| After first nav into list | `tip: press x to mark done, k to kill, Enter to edit` |
| After 5 entries in one session | `tip: Ctrl+B for coaching insights` |
| After 2+ days of use | `tip: press / to search across all your days` |

- Each hint appears for 5 seconds or until next input, then disappears.
- Hints use Textual's built-in `self.notify()` with a timeout — no custom widget needed.
- Hint state stored in `~/.bujo-hints-seen` (simple JSON file).
- Each hint shown exactly once, never repeated.

### AI Classification Feedback

When AI classifies an entry, the type label appears next to it (e.g., `task`, `note`, `event`). This teaches users what types exist by seeing them applied. The type label is already present in the current design — no change needed.

### Help Screen

`?` still opens the full keybinding reference. It remains the comprehensive reference for power users.

---

## Section 3: Navigation & Date Browsing

### Date Ribbon

A horizontal date navigator at the top of the daily view:

```
  <- Mar 16       Monday, March 17 2026       Mar 18 ->
```

- `[` and `]` keys navigate between days from anywhere in the app.
- Today is visually distinct (bold).
- Past days are browsable and show their entries.
- Future days show as empty.
- When viewing a past day, the input area still works but appends to **today's** log.
- The indicator `viewing Mar 16 · typing saves to today` appears **as soon as the user navigates away from today** — not when they start typing. It replaces the greeting line and stays visible the entire time they are viewing a past day. This ensures they see it before typing, not after.
- After submitting an entry while viewing a past day, the view auto-switches to today so the user sees their entry appear. This avoids the confusion of typing something and not seeing it.

### Search

- Press `/` -> a search input appears inline (replaces the date ribbon temporarily).
- Type to search across all daily files. Results show as a filtered list with date labels:

```
  Mar 17  . call Jackson       task
  Mar 15  - feeling scattered   note
  Mar 12  . call Jackson       task  (migrated)
```

- Enter on a result jumps to that day's view with the entry highlighted.
- Escape closes search, returns to current view.
- Search is case-insensitive and matches partial text.
- Search is submit-based, not live: type the query, press Enter to see results. This avoids parsing every markdown file on each keystroke. Results are generated by iterating daily files and calling `parse_entries` on each — no index needed. For vaults under 1000 days this is fast enough.
- **Future optimization — search index:** When performance degrades, introduce `~/bujo-vault/.search-index.json` with the format `{"YYYY-MM-DD": [{"symbol": "t", "text": "..."}], ...}`. Rebuild on vault write; read on search. This is out of scope for v1 but the format is defined here so it's not an afterthought.

### Existing Screens

Monthly (`m`), Future (`f`), Migration (`M`) screens remain unchanged. They are power-user features that work fine and don't need to be discoverable for average users. The help screen (`?`) lists them.

---

## Section 4: Visual Feedback

### Save Confirmation

When an entry is added, the new entry briefly highlights in the list, then settles to normal. No toast, no modal. Implementation: add a CSS class (e.g., `.entry-new`) to the new `ListItem` on mount, with a highlight background. Use `set_timer(1.0, ...)` to remove the class after 1 second.

### Status Change Feedback

- **Mark done:** entry text gets strikethrough/dim styling. Brief inline label `done` fades after 1 second.
- **Kill:** entry dims with `~` prefix. Brief label `killed` fades after 1 second.
- **Migrate:** entry shows `>` and dims. Brief label `migrated` fades after 1 second.
- Entry stays in position during the current view. On next refresh it sorts normally.

### Undo Feedback

- Ctrl+Z shows a one-line notification at the bottom: `undone: mark done "call Jackson"` — disappears after 2 seconds.
- If nothing to undo: `nothing to undo` — disappears after 1 second.

### AI Parsing Indicator

- When AI is classifying (no prefix typed), show `thinking...` next to the input prompt.
- Entry appears when parsing completes.
- If API fails or key isn't set, fall back to saving as a note silently. No error modal.

### Debug Cleanup

- Remove all `bujo-debug.txt` writes from `app.py` and `ai_capture.py`.
- Replace with `logging.debug()` calls gated behind `BUJO_DEBUG=1` environment variable.
- Use Textual's `textual.logging` integration: Textual redirects Python's `logging` to its devtools console, so `logging.debug()` calls won't leak to stderr in production. When `BUJO_DEBUG=1` is set, configure a `FileHandler` writing to `~/bujo-vault/.debug.log` for non-Textual debugging (e.g., CLI commands).

---

## Section 5: Code Architecture

### Current Problem

`app.py` is 1100+ lines handling the app launcher, vault I/O, all screens, all widgets, and symbol definitions. Symbols are duplicated in `app.py` and `models.py`. Debug logging is scattered as raw file writes.

### Proposed Structure

```
bujo/
  app.py              Slim launcher, BuJoApp class only (~50 lines)
  vault.py            All file I/O: ensure_vault, today_path, read/write/append
  symbols.py          Single source of truth for SYMBOLS, SYMBOL_DISPLAY, SYMBOL_COLORS
  undo.py             UndoStack class, session-scoped action history
  hints.py            Progressive disclosure logic, hint state tracking
  views/
    daily.py          DailyView screen (main view)
    monthly.py        MonthlyView screen
    future.py         FutureView screen
    migration.py      MigrationScreen
    help.py           HelpScreen
    search.py         SearchView (new)
  widgets/
    entry_list.py     BuJoListView, EntryItem, inline editing logic
    input_bar.py      Input area with prompt indicator
    date_ribbon.py    Date navigation widget (new)
  models.py           Entry, DayLog, LogReader (unchanged)
  capture.py          parse_quick_input, templates (unchanged)
  ai.py               CLI dump parsing (unchanged)
  ai_capture.py       TUI smart parse (debug writes removed)
  capture_hotkey.py   Global hotkey capture (unchanged)
  analytics.py        InsightsEngine (unchanged)
  integrations.py     Obsidian (unchanged)
  time.py             Greetings (unchanged)
  cli.py              CLI entrypoint (unchanged)
```

### Key Changes

- `symbols.py` becomes single source of truth. Both `models.py` and views import from it.
- `vault.py` extracts all filesystem operations. This is the module a future GUI would swap.
- Views split into individual files, each under 200 lines.
- New modules (`undo.py`, `hints.py`, `search.py`, `date_ribbon.py`) are small and focused.

### Unchanged Modules

`models.py`, `capture.py`, `analytics.py`, `integrations.py`, `time.py`, `cli.py`, `ai.py`, `capture_hotkey.py` — all solid, no changes needed except imports from the new `symbols.py`.

### Test Migration Strategy

The refactor moves symbols to `symbols.py`, vault I/O to `vault.py`, and splits views into separate files. Existing tests import from `bujo.app` (e.g., `SYMBOLS`, `VAULT`, `append_entry`, `ensure_vault`). To avoid breaking all tests at once:

- `app.py` re-exports key names from the new modules (`from bujo.symbols import *`, `from bujo.vault import *`) so existing imports continue to work.
- New tests import from the specific modules (`bujo.symbols`, `bujo.vault`, etc.).
- Old test imports are migrated incrementally — not a blocker for the initial refactor.

---

## Section 6: What Stays the Same

- Plain markdown files in `~/bujo-vault/`. Obsidian-compatible.
- All CLI commands (`bujo log`, `bujo coach`, `bujo dump`, etc.).
- Monthly, Future, Migration screens for power users.
- Coaching with Ctrl+B. AI dump with Ctrl+D.
- Global hotkey capture (`Win+Shift+B`).
- Symbol system (ASCII in files, Unicode in TUI).
- Prefix system (still works, just not required).
- All existing tests continue to pass.

---

## Out of Scope

- GUI (web/desktop) — future project, this spec is TUI only.
- New AI features beyond current smart parse and dump.
- Mobile support.
- Multi-user or sync features.
- Changes to the vault file format.
