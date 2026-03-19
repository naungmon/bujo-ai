# BuJo-AI Notepad Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the bujo-ai TUI to feel like a notepad — always-ready input, no modes, inline editing, progressive hints, undo, date browsing, and search — while preserving all existing CLI and power-user functionality.

**Architecture:** Extract the monolithic `app.py` (1100+ lines) into focused modules: `symbols.py`, `vault.py`, `undo.py`, `hints.py`, `views/`, `widgets/`. The DailyView is rebuilt around a modeless interaction model where arrow keys naturally move between input and entries. Existing tests continue to pass via re-exports from `app.py`.

**Tech Stack:** Python 3.10+, Textual >=0.47.0, pytest, OpenRouter API (via requests/urllib)

**Spec:** `docs/superpowers/specs/2026-03-17-bujo-ai-notepad-redesign-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `bujo/symbols.py` | Single source of truth: SYMBOLS, SYMBOL_DISPLAY, SYMBOL_COLORS, ENTRY_SORT_ORDER |
| `bujo/vault.py` | All vault I/O: VAULT, DAILY, ensure_vault, today_path, today_log, save_today, append_entry, read_text_safe, get_monthly_path, get_future_path, has_any_daily_files, get_all_logs_summary, open_in_editor |
| `bujo/undo.py` | UndoAction dataclass + UndoStack class |
| `bujo/hints.py` | HintManager: milestone tracking, state persistence to ~/.bujo-hints-seen |
| `bujo/views/__init__.py` | Empty init |
| `bujo/views/daily.py` | Redesigned DailyView screen (main view, no modes) |
| `bujo/views/monthly.py` | MonthlyView screen (extracted from app.py) |
| `bujo/views/future.py` | FutureView screen (extracted from app.py) |
| `bujo/views/migration.py` | MigrationScreen (extracted from app.py) |
| `bujo/views/help.py` | HelpScreen (extracted, updated content) |
| `bujo/views/search.py` | SearchView screen (new) |
| `bujo/widgets/__init__.py` | Empty init |
| `bujo/widgets/entry_list.py` | BuJoListView, EntryItem with inline editing |
| `bujo/widgets/input_bar.py` | BuJoInput (TextArea subclass with arrow-up focus transfer) |
| `bujo/widgets/date_ribbon.py` | DateRibbon widget |
| `tests/test_symbols.py` | Tests for symbols.py |
| `tests/test_vault.py` | Tests for vault.py |
| `tests/test_undo.py` | Tests for undo.py |
| `tests/test_hints.py` | Tests for hints.py |
| `tests/test_search.py` | Tests for search logic |
| `tests/test_widgets.py` | Tests for DateRibbon, BuJoInput, EntryItem, BuJoListView |

### Modified Files

| File | Changes |
|------|---------|
| `bujo/app.py` | Gut to ~50 lines: BuJoApp class + re-exports from symbols.py and vault.py |
| `bujo/app.tcss` | Add CSS for date ribbon, inline edit, entry-new animation, search |
| `bujo/models.py` | Import SYMBOLS/SYMBOL_DISPLAY from symbols.py instead of defining locally |
| `bujo/ai_capture.py` | Remove all bujo-debug.txt writes, replace with logging.debug(), add decision flow comment |

### Unchanged Files

`bujo/capture.py`, `bujo/ai.py`, `bujo/analytics.py`, `bujo/integrations.py`, `bujo/time.py`, `bujo/cli.py`, `bujo/capture_hotkey.py`

---

## Task 1: Create `symbols.py` — Single Source of Truth

**Files:**
- Create: `bujo/symbols.py`
- Modify: `bujo/models.py` (lines 8-37 — remove SYMBOLS/SYMBOL_DISPLAY/LEGACY_UNICODE_TO_ASCII, import from symbols)
- Modify: `bujo/app.py` (lines 26-59 — remove SYMBOLS/SYMBOL_DISPLAY/SYMBOL_COLORS/NAV_ACTIONS/ENTRY_SORT_ORDER, import from symbols)
- Test: `tests/test_symbols.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_symbols.py
"""Tests for bujo.symbols — canonical symbol definitions."""

from bujo.symbols import (
    SYMBOLS,
    SYMBOL_DISPLAY,
    SYMBOL_COLORS,
    LEGACY_UNICODE_TO_ASCII,
    ENTRY_SORT_ORDER,
)


class TestSymbols:
    def test_all_symbols_defined(self):
        expected = {"t", "x", ">", "k", "n", "e", "*"}
        assert set(SYMBOLS.keys()) == expected

    def test_all_displays_defined(self):
        assert set(SYMBOL_DISPLAY.keys()) == set(SYMBOLS.keys())

    def test_all_colors_defined(self):
        assert set(SYMBOL_COLORS.keys()) == set(SYMBOLS.keys())

    def test_legacy_maps_back_to_ascii(self):
        for uni, ascii_sym in LEGACY_UNICODE_TO_ASCII.items():
            assert ascii_sym in SYMBOLS

    def test_sort_order_covers_all(self):
        assert set(ENTRY_SORT_ORDER.keys()) == set(SYMBOLS.keys())

    def test_priority_sorts_first(self):
        assert ENTRY_SORT_ORDER["*"] < ENTRY_SORT_ORDER["t"]

    def test_display_unicode_not_ascii(self):
        # Task display is · (U+00B7), not plain dot
        assert SYMBOL_DISPLAY["t"] == "\u00b7"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest tests/test_symbols.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bujo.symbols'`

- [ ] **Step 3: Create `bujo/symbols.py`**

```python
"""Canonical symbol definitions for BuJo.

Single source of truth. All other modules import from here.
"""

# ASCII symbols stored in markdown files
SYMBOLS = {
    "t": ("Task", "Something to do"),
    "x": ("Done", "Completed"),
    ">": ("Migrated", "Moved forward"),
    "k": ("Killed", "Consciously dropped"),
    "n": ("Note", "Thought or observation"),
    "e": ("Event", "Happened or scheduled"),
    "*": ("Priority", "This one matters today"),
}

# TUI display symbols (Unicode render)
SYMBOL_DISPLAY = {
    "t": "\u00b7",  # ·
    "x": "\u00d7",  # ×
    ">": ">",
    "k": "~",
    "n": "\u2013",  # –
    "e": "\u25cb",  # ○
    "*": "\u2605",  # ★
}

# TUI colors per symbol
SYMBOL_COLORS = {
    "t": "cyan",
    "x": "green",
    ">": "blue",
    "k": "dim",
    "n": "white",
    "e": "magenta",
    "*": "red",
}

# Legacy Unicode -> ASCII mapping for backward compatibility
LEGACY_UNICODE_TO_ASCII = {
    "\u00b7": "t",
    "\u00d7": "x",
    "~": "k",
    "\u2013": "n",
    "\u25cb": "e",
    "\u2605": "*",
}

# Sort order for entry display (priority first, done/migrated last)
ENTRY_SORT_ORDER = {"*": 0, "t": 1, "e": 2, "n": 3, "k": 4, "x": 5, ">": 6}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest tests/test_symbols.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Update `bujo/models.py` to import from symbols**

Replace lines 8-37 in `bujo/models.py` (the SYMBOLS, SYMBOL_DISPLAY, LEGACY_UNICODE_TO_ASCII definitions) with:
```python
from bujo.symbols import SYMBOLS, SYMBOL_DISPLAY, LEGACY_UNICODE_TO_ASCII
```

- [ ] **Step 6: Update `bujo/app.py` to import from symbols**

Replace lines 26-59 in `bujo/app.py` (the SYMBOLS, SYMBOL_DISPLAY, SYMBOL_COLORS, NAV_ACTIONS, ENTRY_SORT_ORDER definitions) with:
```python
from bujo.symbols import SYMBOLS, SYMBOL_DISPLAY, SYMBOL_COLORS, ENTRY_SORT_ORDER

NAV_ACTIONS = {"x": "x", "k": "k", ">": ">"}
```

Keep NAV_ACTIONS in app.py — it's a UI concern, not a symbol definition.

- [ ] **Step 7: Run all existing tests**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest -v`
Expected: ALL tests pass (existing + new). This verifies the extraction didn't break anything.

- [ ] **Step 8: Commit**

```bash
git add bujo/symbols.py bujo/models.py bujo/app.py tests/test_symbols.py
git commit -m "refactor: extract symbols.py as single source of truth for symbol definitions"
```

---

## Task 2: Create `vault.py` — Vault I/O Extraction

**Files:**
- Create: `bujo/vault.py`
- Modify: `bujo/app.py` (remove vault functions, import from vault.py)
- Test: `tests/test_vault.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_vault.py
"""Tests for bujo.vault — vault file I/O operations."""

import os
from datetime import date
from pathlib import Path

import pytest

from bujo.vault import (
    ensure_vault,
    today_path,
    today_log,
    save_today,
    append_entry,
    read_text_safe,
    get_monthly_path,
    get_future_path,
    has_any_daily_files,
)


class TestEnsureVault:
    def test_creates_directories(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path / "test-vault"))
        # Re-import to pick up new env
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        bujo.vault.ensure_vault()
        assert (tmp_path / "test-vault" / "daily").is_dir()
        assert (tmp_path / "test-vault" / "monthly").is_dir()
        assert (tmp_path / "test-vault" / "future").is_dir()


class TestAppendEntry:
    def test_creates_file_and_appends(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        bujo.vault.ensure_vault()
        bujo.vault.append_entry("t", "buy milk")
        p = bujo.vault.today_path()
        content = p.read_text(encoding="utf-8")
        assert "t buy milk" in content

    def test_appends_to_existing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        bujo.vault.ensure_vault()
        bujo.vault.append_entry("t", "first")
        bujo.vault.append_entry("n", "second")
        content = bujo.vault.today_path().read_text(encoding="utf-8")
        assert "t first" in content
        assert "n second" in content


class TestReadTextSafe:
    def test_utf8(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("hello", encoding="utf-8")
        assert read_text_safe(p) == "hello"

    def test_missing_file(self, tmp_path):
        assert read_text_safe(tmp_path / "nope.md") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest tests/test_vault.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bujo.vault'`

- [ ] **Step 3: Create `bujo/vault.py`**

Extract the following functions from `bujo/app.py` (lines 19-146) into `bujo/vault.py`:
- Module-level constants: `VAULT`, `DAILY`, `FUTURE`, `MONTHLY`, `REFLECTIONS`, `FIRST_RUN_FLAG`
- Functions: `open_in_editor`, `ensure_vault`, `today_path`, `read_text_safe`, `today_log`, `save_today`, `append_entry`, `get_monthly_path`, `get_future_path`, `has_any_daily_files`, `get_all_logs_summary`

```python
"""Vault file I/O for BuJo.

All filesystem operations live here. This is the module a future
GUI would swap out for its own storage backend.
"""

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

VAULT = Path(os.environ.get("BUJO_VAULT", Path.home() / "bujo-vault"))
DAILY = VAULT / "daily"
FUTURE = VAULT / "future"
MONTHLY = VAULT / "monthly"
REFLECTIONS = VAULT / "reflections"
FIRST_RUN_FLAG = Path.home() / ".bujo-first-run-done"


def open_in_editor(path: Path | str) -> None:
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        editor = "notepad" if sys.platform == "win32" else "nano"
    try:
        subprocess.run([editor, str(path)], check=False)
    except FileNotFoundError:
        pass


def ensure_vault() -> None:
    for d in [DAILY, FUTURE, MONTHLY, REFLECTIONS]:
        d.mkdir(parents=True, exist_ok=True)


def today_path() -> Path:
    return DAILY / f"{date.today().isoformat()}.md"


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")
    except (OSError, PermissionError):
        return ""


def today_log() -> str:
    p = today_path()
    if not p.exists():
        header = f"# {date.today().strftime('%A, %B %d %Y')}\n\n"
        p.write_text(header, encoding="utf-8")
    return read_text_safe(p)


def save_today(content: str) -> None:
    today_path().write_text(content, encoding="utf-8")


def append_entry(symbol: str, text: str) -> None:
    p = today_path()
    if not p.exists():
        today_log()
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"{symbol} {text}\n")


def get_monthly_path() -> Path:
    return MONTHLY / f"{date.today().strftime('%Y-%m')}.md"


def get_future_path() -> Path:
    return FUTURE / "future.md"


def has_any_daily_files() -> bool:
    if not DAILY.exists():
        return False
    return any(DAILY.glob("*.md"))


def get_all_logs_summary() -> str:
    lines: list[str] = []
    daily_files = sorted(DAILY.glob("*.md"), reverse=True)[:7]
    for f in daily_files:
        lines.append(f"\n## {f.stem}")
        try:
            lines.append(read_text_safe(f).strip())
        except (OSError, PermissionError):
            lines.append("_(could not read file)_")
    future = get_future_path()
    if future.exists():
        lines.append("\n## Future Log")
        try:
            lines.append(read_text_safe(future).strip())
        except (OSError, PermissionError):
            lines.append("_(could not read file)_")
    monthly = get_monthly_path()
    if monthly.exists():
        lines.append(f"\n## Monthly ({date.today().strftime('%B %Y')})")
        try:
            lines.append(read_text_safe(monthly).strip())
        except (OSError, PermissionError):
            lines.append("_(could not read file)_")
    return "\n".join(lines)
```

- [ ] **Step 4: Update `bujo/app.py` to import from vault.py**

Replace lines 19-146 in `app.py` with:
```python
from bujo.vault import (
    VAULT, DAILY, FUTURE, MONTHLY, REFLECTIONS, FIRST_RUN_FLAG,
    open_in_editor, ensure_vault, today_path, read_text_safe,
    today_log, save_today, append_entry, get_monthly_path,
    get_future_path, has_any_daily_files, get_all_logs_summary,
)
```

Also add re-exports at the bottom of `app.py` for backward compat — but since we're importing at module level with the same names, they're already available as `bujo.app.VAULT`, etc.

- [ ] **Step 5: Run all tests**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest -v`
Expected: ALL tests pass. Existing tests import from `bujo.app` and still find the same names.

- [ ] **Step 6: Commit**

```bash
git add bujo/vault.py bujo/app.py tests/test_vault.py
git commit -m "refactor: extract vault.py for all file I/O operations"
```

---

## Task 3: Debug Cleanup

**Files:**
- Modify: `bujo/app.py` (remove lines 857-858, 999-1000 — bujo-debug.txt writes)
- Modify: `bujo/ai_capture.py` (remove all bujo-debug.txt writes, add logging + decision flow comment)

- [ ] **Step 1: Remove debug writes from `bujo/app.py`**

Remove these lines:
- Line 857-858: `with open("C:/Users/User/Desktop/bujo-debug.txt", "a") as _dbg: _dbg.write(...)`
- Line 999-1000: Same pattern in `on_key`

- [ ] **Step 2: Replace debug writes in `bujo/ai_capture.py`**

Replace all `with open("C:/Users/User/Desktop/bujo-debug.txt", "a") as _dbg:` blocks with `logging.debug()` calls. Add at the top of the file:

```python
import logging

logger = logging.getLogger(__name__)
```

Add the decision flow comment at the top of `smart_parse`:
```python
def smart_parse(text: str) -> list[tuple[str, str]]:
    """Parse input text, using AI when no explicit prefix is detected.

    Decision flow (see spec Section 1):
      has_explicit_prefix(text)?
        YES -> parse_quick_input(text) -> (symbol, cleaned) -> [single entry]
        NO  -> ai_parse_dump(text)
                 API success -> [(symbol, text), ...] -> [multiple entries]
                 API failure -> fallback: [("n", text)] -> [single note]
    """
```

Configure logging at module level:
```python
if os.environ.get("BUJO_DEBUG") == "1":
    _handler = logging.FileHandler(Path.home() / "bujo-vault" / ".debug.log")
    _handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.DEBUG)
```

- [ ] **Step 3: Run all tests**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest -v`
Expected: ALL tests pass.

- [ ] **Step 4: Commit**

```bash
git add bujo/app.py bujo/ai_capture.py
git commit -m "fix: replace debug file writes with logging module"
```

---

## Task 4: Create `undo.py`

**Files:**
- Create: `bujo/undo.py`
- Test: `tests/test_undo.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_undo.py
"""Tests for bujo.undo — session-scoped undo stack."""

from pathlib import Path

import pytest

from bujo.undo import UndoAction, UndoStack


class TestUndoAction:
    def test_fields(self):
        a = UndoAction(
            action_type="add",
            file_path=Path("daily/2026-03-17.md"),
            original_line="",
            new_line="t buy milk",
            description='add "buy milk"',
        )
        assert a.action_type == "add"
        assert a.new_line == "t buy milk"


class TestUndoStack:
    def test_empty_pop_returns_none(self):
        stack = UndoStack()
        assert stack.pop() is None

    def test_push_and_pop(self):
        stack = UndoStack()
        a = UndoAction("add", Path("f.md"), "", "t test", "add")
        stack.push(a)
        assert stack.pop() == a

    def test_lifo_order(self):
        stack = UndoStack()
        a1 = UndoAction("add", Path("f.md"), "", "t first", "add first")
        a2 = UndoAction("add", Path("f.md"), "", "t second", "add second")
        stack.push(a1)
        stack.push(a2)
        assert stack.pop() == a2
        assert stack.pop() == a1

    def test_is_empty(self):
        stack = UndoStack()
        assert stack.is_empty
        stack.push(UndoAction("add", Path("f.md"), "", "t x", "add"))
        assert not stack.is_empty

    def test_apply_undo_add(self, tmp_path):
        """Undo an 'add' removes the new_line from the file."""
        f = tmp_path / "test.md"
        f.write_text("# Header\n\nt buy milk\n", encoding="utf-8")
        stack = UndoStack()
        action = UndoAction("add", f, "", "t buy milk", 'add "buy milk"')
        stack.push(action)
        result = stack.undo()
        assert result is not None
        content = f.read_text(encoding="utf-8")
        assert "t buy milk" not in content
        assert "# Header" in content

    def test_apply_undo_status_change(self, tmp_path):
        """Undo a status change restores original_line."""
        f = tmp_path / "test.md"
        f.write_text("# Header\n\nx buy milk\n", encoding="utf-8")
        stack = UndoStack()
        action = UndoAction("status_change", f, "t buy milk", "x buy milk", "mark done")
        stack.push(action)
        result = stack.undo()
        assert result is not None
        content = f.read_text(encoding="utf-8")
        assert "t buy milk" in content
        assert "x buy milk" not in content

    def test_apply_undo_edit(self, tmp_path):
        """Undo an edit restores original text."""
        f = tmp_path / "test.md"
        f.write_text("# Header\n\nt buy oat milk\n", encoding="utf-8")
        stack = UndoStack()
        action = UndoAction("edit", f, "t buy milk", "t buy oat milk", "edit")
        stack.push(action)
        result = stack.undo()
        assert result is not None
        content = f.read_text(encoding="utf-8")
        assert "t buy milk" in content
        assert "t buy oat milk" not in content

    def test_undo_empty_returns_none(self):
        stack = UndoStack()
        assert stack.undo() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest tests/test_undo.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `bujo/undo.py`**

```python
"""Session-scoped undo stack for BuJo.

Each action (add, edit, status_change) is recorded with enough
information to reverse it by modifying the markdown file directly.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class UndoAction:
    action_type: str        # "add", "edit", "status_change"
    file_path: Path         # which markdown file was modified
    original_line: str      # line content before action ("" for add)
    new_line: str           # line content after action
    description: str        # human-readable, e.g. 'mark done "call Jackson"'


class UndoStack:
    """Session-scoped undo stack. Clears on app close."""

    def __init__(self) -> None:
        self._stack: list[UndoAction] = []

    def push(self, action: UndoAction) -> None:
        self._stack.append(action)

    def pop(self) -> UndoAction | None:
        return self._stack.pop() if self._stack else None

    @property
    def is_empty(self) -> bool:
        return len(self._stack) == 0

    def undo(self) -> UndoAction | None:
        """Pop the last action and reverse it in the file.

        Returns the undone action, or None if stack is empty.
        """
        action = self.pop()
        if action is None:
            return None

        try:
            content = action.file_path.read_text(encoding="utf-8")
        except (OSError, PermissionError):
            return action  # can't read file, but still return the action

        if action.action_type == "add":
            # Remove the LAST occurrence of new_line (newest entry is at end of file)
            idx = content.rfind(action.new_line + "\n")
            if idx != -1:
                content = content[:idx] + content[idx + len(action.new_line) + 1:]
        elif action.action_type in ("edit", "status_change"):
            # Replace new_line with original_line
            content = content.replace(action.new_line, action.original_line, 1)

        action.file_path.write_text(content, encoding="utf-8")
        return action
```

- [ ] **Step 4: Run tests**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest tests/test_undo.py -v`
Expected: ALL pass

- [ ] **Step 5: Run full suite**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest -v`
Expected: ALL pass

- [ ] **Step 6: Commit**

```bash
git add bujo/undo.py tests/test_undo.py
git commit -m "feat: add session-scoped undo stack"
```

---

## Task 5: Create `hints.py`

**Files:**
- Create: `bujo/hints.py`
- Test: `tests/test_hints.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_hints.py
"""Tests for bujo.hints — progressive disclosure system."""

import json
from pathlib import Path

import pytest

from bujo.hints import HintManager


class TestHintManager:
    def test_first_entry_hint(self, tmp_path):
        mgr = HintManager(state_path=tmp_path / "hints.json")
        hint = mgr.check("first_entry")
        assert hint is not None
        assert "tip:" in hint

    def test_hint_shown_once(self, tmp_path):
        mgr = HintManager(state_path=tmp_path / "hints.json")
        first = mgr.check("first_entry")
        assert first is not None
        second = mgr.check("first_entry")
        assert second is None

    def test_state_persists(self, tmp_path):
        state_file = tmp_path / "hints.json"
        mgr1 = HintManager(state_path=state_file)
        mgr1.check("first_entry")
        # New instance reads persisted state
        mgr2 = HintManager(state_path=state_file)
        assert mgr2.check("first_entry") is None

    def test_unknown_milestone_returns_none(self, tmp_path):
        mgr = HintManager(state_path=tmp_path / "hints.json")
        assert mgr.check("nonexistent_milestone") is None

    def test_all_milestones_defined(self, tmp_path):
        mgr = HintManager(state_path=tmp_path / "hints.json")
        expected = {"first_entry", "three_entries", "first_nav", "five_entries_session", "multi_day"}
        assert set(mgr.HINTS.keys()) == expected

    def test_entry_count_check(self, tmp_path):
        mgr = HintManager(state_path=tmp_path / "hints.json")
        assert mgr.check_entry_count(0) is None
        hint = mgr.check_entry_count(1)
        assert hint is not None  # first_entry hint
        assert mgr.check_entry_count(1) is None  # already shown
        hint3 = mgr.check_entry_count(3)
        assert hint3 is not None  # three_entries hint
        hint5 = mgr.check_entry_count(5)
        assert hint5 is not None  # five_entries_session hint
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest tests/test_hints.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `bujo/hints.py`**

```python
"""Progressive disclosure hints for BuJo.

Shows milestone-triggered hints exactly once. State persists
in ~/.bujo-hints-seen (JSON file).
"""

import json
from pathlib import Path


class HintManager:
    """Tracks which hints have been shown and triggers new ones at milestones."""

    HINTS = {
        "first_entry": 'tip: start with "t" for task, "e" for event, or just type naturally',
        "three_entries": "tip: use arrow keys to browse your entries",
        "first_nav": "tip: press x to mark done, k to kill, Enter to edit",
        "five_entries_session": "tip: Ctrl+B for coaching insights",
        "multi_day": "tip: press / to search across all your days",
    }

    def __init__(self, state_path: Path | None = None) -> None:
        self._state_path = state_path or (Path.home() / ".bujo-hints-seen")
        self._seen: set[str] = set()
        self._load()

    def _load(self) -> None:
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                self._seen = set(data.get("seen", []))
            except (json.JSONDecodeError, OSError):
                self._seen = set()

    def _save(self) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(
                json.dumps({"seen": list(self._seen)}),
                encoding="utf-8",
            )
        except OSError:
            pass

    def check(self, milestone: str) -> str | None:
        """Check if a hint should be shown for this milestone.

        Returns the hint text if it hasn't been shown yet, None otherwise.
        Marks the hint as seen.
        """
        if milestone not in self.HINTS:
            return None
        if milestone in self._seen:
            return None
        self._seen.add(milestone)
        self._save()
        return self.HINTS[milestone]

    def check_entry_count(self, count: int) -> str | None:
        """Check entry-count-based milestones. Call after each new entry."""
        if count >= 1:
            hint = self.check("first_entry")
            if hint:
                return hint
        if count >= 3:
            hint = self.check("three_entries")
            if hint:
                return hint
        if count >= 5:
            hint = self.check("five_entries_session")
            if hint:
                return hint
        return None
```

- [ ] **Step 4: Run tests**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest tests/test_hints.py -v`
Expected: ALL pass

- [ ] **Step 5: Commit**

```bash
git add bujo/hints.py tests/test_hints.py
git commit -m "feat: add progressive disclosure hint system"
```

---

## Task 6: Create `widgets/input_bar.py` — TextArea Subclass

**Files:**
- Create: `bujo/widgets/__init__.py`
- Create: `bujo/widgets/input_bar.py`

- [ ] **Step 1: Create `bujo/widgets/__init__.py`**

```python
"""BuJo TUI widgets."""
```

- [ ] **Step 2: Create `bujo/widgets/input_bar.py`**

```python
"""BuJo input bar — TextArea subclass with focus transfer on arrow-up.

When the cursor is on the first line (or the TextArea is empty),
arrow-up transfers focus to the entry list instead of moving the
cursor within the TextArea.
"""

from textual.widgets import TextArea
from textual import events


class BuJoInput(TextArea):
    """Main input TextArea that transfers focus on arrow-up at first line."""

    def _on_key(self, event: events.Key) -> None:
        if event.key == "up":
            # Transfer focus if on first line or empty
            cursor_row = self.cursor_location[0]
            if cursor_row == 0 or not self.text.strip():
                try:
                    entry_list = self.screen.query_one("#entry-list")
                    if entry_list.children:
                        entry_list.focus()
                        event.prevent_default()
                        event.stop()
                        return
                except Exception:
                    pass
        super()._on_key(event)
```

- [ ] **Step 3: Verify import works**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -c "from bujo.widgets.input_bar import BuJoInput; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add bujo/widgets/__init__.py bujo/widgets/input_bar.py
git commit -m "feat: add BuJoInput widget with arrow-up focus transfer"
```

---

## Task 7: Create `widgets/entry_list.py` — ListView with Inline Editing

**Files:**
- Create: `bujo/widgets/entry_list.py`

- [ ] **Step 1: Create `bujo/widgets/entry_list.py`**

```python
"""BuJo entry list — ListView with inline editing support.

EntryItem displays an entry as a Static widget. When Enter is pressed,
the Static is replaced with an Input for inline editing. Enter saves,
Escape cancels.
"""

from textual.widgets import ListView, ListItem, Static, Input
from textual.app import ComposeResult
from textual import on

from bujo.symbols import SYMBOL_DISPLAY, SYMBOL_COLORS


class BuJoListView(ListView):
    """ListView subclass that clamps stale index before cursor actions."""

    def _clamp_index(self) -> None:
        if self._nodes and self.index is not None and self.index >= len(self._nodes):
            self.index = len(self._nodes) - 1

    def action_cursor_up(self) -> None:
        self._clamp_index()
        super().action_cursor_up()

    def action_cursor_down(self) -> None:
        self._clamp_index()
        # If at bottom of list, transfer focus to input
        if self.index is not None and self._nodes and self.index >= len(self._nodes) - 1:
            try:
                inp = self.screen.query_one("#main-input")
                inp.focus()
                return
            except Exception:
                pass
        super().action_cursor_down()


def format_entry(entry) -> str:
    """Format an Entry object or dict as markup for ListView."""
    if hasattr(entry, "symbol"):
        sym, display, text, etype = entry.symbol, entry.display, entry.text, entry.type
    else:
        sym = entry.get("symbol", "")
        display = entry.get("display", "")
        text = entry.get("text", "")
        etype = entry.get("type", "")

    color = SYMBOL_COLORS.get(sym, "white")
    if sym == "x":
        return f"[{color} dim]{display}[/] [dim]{text}[/]  [dim italic]{etype}[/]"
    elif sym == "k":
        return f"[dim]{display}[/] [dim]{text}[/]  [dim italic]{etype}[/]"
    elif sym == "*":
        return f"[{color} bold]{display}[/] [bold]{text}[/]  [dim italic]{etype}[/]"
    else:
        return f"[{color}]{display}[/] [white]{text}[/]  [dim italic]{etype}[/]"


class EntryItem(ListItem):
    """A list item representing a BuJo entry, with inline edit support."""

    def __init__(self, entry, index: int) -> None:
        super().__init__()
        self.entry = entry
        self.entry_index = index
        self._editing = False

    def compose(self) -> ComposeResult:
        yield Static(format_entry(self.entry), id="entry-display")

    def start_edit(self) -> None:
        """Replace Static with Input for inline editing."""
        if self._editing:
            return
        self._editing = True
        text = self.entry.get("text", "") if isinstance(self.entry, dict) else self.entry.text
        display = self.query_one("#entry-display", Static)
        display.display = False
        edit_input = Input(value=text, id="inline-edit")
        self.mount(edit_input)
        edit_input.focus()

    def cancel_edit(self) -> None:
        """Remove Input, restore Static."""
        if not self._editing:
            return
        self._editing = False
        try:
            self.query_one("#inline-edit", Input).remove()
        except Exception:
            pass
        self.query_one("#entry-display", Static).display = True

    @property
    def is_editing(self) -> bool:
        return self._editing
```

- [ ] **Step 2: Verify import works**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -c "from bujo.widgets.entry_list import BuJoListView, EntryItem; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add bujo/widgets/entry_list.py
git commit -m "feat: add entry list widget with inline editing support"
```

---

## Task 8: Create `widgets/date_ribbon.py`

**Files:**
- Create: `bujo/widgets/date_ribbon.py`

- [ ] **Step 1: Create `bujo/widgets/date_ribbon.py`**

```python
"""Date ribbon widget — horizontal day navigator.

Shows: <- Mar 16       Monday, March 17 2026       Mar 18 ->
Supports [ and ] keys for navigation.
"""

from datetime import date, timedelta

from textual.widgets import Static
from textual.reactive import reactive


class DateRibbon(Static):
    """Displays current viewing date with prev/next indicators."""

    viewing_date: reactive[date] = reactive(date.today)

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)

    def watch_viewing_date(self, value: date) -> None:
        self._render_ribbon()

    def on_mount(self) -> None:
        self._render_ribbon()

    def _render_ribbon(self) -> None:
        d = self.viewing_date
        today = date.today()
        prev_day = d - timedelta(days=1)
        next_day = d + timedelta(days=1)

        prev_label = prev_day.strftime("%b %d")
        next_label = next_day.strftime("%b %d")
        center = d.strftime("%A, %B %d %Y")

        if d == today:
            center_fmt = f"[bold]{center}[/bold]"
        else:
            center_fmt = f"[dim]{center}[/dim]"

        self.update(
            f"  [dim]<[/dim] {prev_label}       {center_fmt}       {next_label} [dim]>[/dim]"
        )

    def go_prev(self) -> None:
        self.viewing_date = self.viewing_date - timedelta(days=1)

    def go_next(self) -> None:
        """Navigate to next day. Future days are allowed (spec says they show as empty)."""
        self.viewing_date = self.viewing_date + timedelta(days=1)

    @property
    def is_viewing_today(self) -> bool:
        return self.viewing_date == date.today()
```

- [ ] **Step 2: Verify import**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -c "from bujo.widgets.date_ribbon import DateRibbon; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add bujo/widgets/date_ribbon.py
git commit -m "feat: add date ribbon widget for day navigation"
```

- [ ] **Step 4: Create `tests/test_widgets.py` — unit tests for all widgets**

```python
# tests/test_widgets.py
"""Tests for BuJo widgets — DateRibbon, BuJoListView, EntryItem, BuJoInput."""

from datetime import date, timedelta

import pytest

from bujo.widgets.date_ribbon import DateRibbon


class TestDateRibbon:
    def test_go_prev_decrements(self):
        ribbon = DateRibbon()
        ribbon.viewing_date = date(2026, 3, 17)
        ribbon.go_prev()
        assert ribbon.viewing_date == date(2026, 3, 16)

    def test_go_next_increments(self):
        ribbon = DateRibbon()
        ribbon.viewing_date = date(2026, 3, 16)
        ribbon.go_next()
        assert ribbon.viewing_date == date(2026, 3, 17)

    def test_go_next_allows_future(self):
        """Spec says future days show as empty, so navigation must not be blocked."""
        ribbon = DateRibbon()
        ribbon.viewing_date = date.today()
        ribbon.go_next()
        assert ribbon.viewing_date == date.today() + timedelta(days=1)

    def test_is_viewing_today(self):
        ribbon = DateRibbon()
        ribbon.viewing_date = date.today()
        assert ribbon.is_viewing_today
        ribbon.go_prev()
        assert not ribbon.is_viewing_today
```

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest tests/test_widgets.py -v`
Expected: ALL pass

- [ ] **Step 5: Commit widget tests**

```bash
git add tests/test_widgets.py
git commit -m "test: add unit tests for DateRibbon widget"
```

---

## Task 9: Extract Secondary Views

**Files:**
- Create: `bujo/views/__init__.py`
- Create: `bujo/views/monthly.py`
- Create: `bujo/views/future.py`
- Create: `bujo/views/migration.py`
- Create: `bujo/views/help.py`

- [ ] **Step 1: Create `bujo/views/__init__.py`**

```python
"""BuJo TUI views (screens)."""
```

- [ ] **Step 2: Extract `bujo/views/monthly.py`**

Move `MonthlyView` class from `bujo/app.py` (lines 202-262) into `bujo/views/monthly.py`. Update imports to use `bujo.vault` and `bujo.symbols`.

- [ ] **Step 3: Extract `bujo/views/future.py`**

Move `FutureView` class from `bujo/app.py` (lines 264-318) into `bujo/views/future.py`. Update imports.

- [ ] **Step 4: Extract `bujo/views/migration.py`**

Move `MigrationScreen` class from `bujo/app.py` (lines 321-447) into `bujo/views/migration.py`. Update imports. For `EntryItem`, import from `bujo.app` temporarily (it still lives there at this point). The import will be updated to `bujo.widgets.entry_list` in Task 11 when the old code is removed.

- [ ] **Step 5: Extract `bujo/views/help.py`**

Move `HelpScreen` class from `bujo/app.py` (lines 450-489). Update the help content to reflect the new interaction model:
- Remove the "Escape to enter, Escape to exit" mode description
- Replace with "arrow up/down to browse, Enter to edit"
- Add `[` `]` for date navigation
- Add `/` for search
- Add Ctrl+Z for undo
- Keep m/f/M/Ctrl+B/?/q

- [ ] **Step 6: Update `bujo/app.py`**

Replace the extracted class definitions with imports:
```python
from bujo.views.monthly import MonthlyView
from bujo.views.future import FutureView
from bujo.views.migration import MigrationScreen
from bujo.views.help import HelpScreen
```

- [ ] **Step 7: Run all tests**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest -v`
Expected: ALL tests pass. The views are used by name in `app.py`'s DailyView — they just need to be importable.

- [ ] **Step 8: Commit**

```bash
git add bujo/views/ bujo/app.py
git commit -m "refactor: extract secondary views into bujo/views/"
```

---

## Task 10: Create `views/search.py`

**Files:**
- Create: `bujo/views/search.py`
- Test: `tests/test_search.py`

- [ ] **Step 1: Write the test for search logic**

```python
# tests/test_search.py
"""Tests for search across vault entries."""

from datetime import date
from pathlib import Path

import pytest

from bujo.views.search import search_vault


class TestSearchVault:
    def _create_vault(self, tmp_path, files: dict[str, str]) -> Path:
        daily = tmp_path / "daily"
        daily.mkdir(parents=True)
        for name, content in files.items():
            (daily / name).write_text(content, encoding="utf-8")
        return tmp_path

    def test_finds_matching_entries(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-17.md": "# Wednesday, March 17 2026\n\nt call Jackson\nn feeling good",
            "2026-03-16.md": "# Tuesday, March 16 2026\n\nt buy milk\nt call Jackson again",
        })
        results = search_vault("jackson", vault)
        assert len(results) == 2
        assert all("jackson" in r["text"].lower() for r in results)

    def test_case_insensitive(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-17.md": "# Wednesday, March 17 2026\n\nt Call JACKSON",
        })
        results = search_vault("jackson", vault)
        assert len(results) == 1

    def test_no_results(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-17.md": "# Wednesday, March 17 2026\n\nt buy milk",
        })
        results = search_vault("nonexistent", vault)
        assert results == []

    def test_results_include_date(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-17.md": "# Wednesday, March 17 2026\n\nt buy milk",
        })
        results = search_vault("milk", vault)
        assert results[0]["date"] == "2026-03-17"

    def test_results_sorted_newest_first(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-15.md": "# Saturday, March 15 2026\n\nt milk",
            "2026-03-17.md": "# Monday, March 17 2026\n\nt milk",
            "2026-03-16.md": "# Sunday, March 16 2026\n\nt milk",
        })
        results = search_vault("milk", vault)
        dates = [r["date"] for r in results]
        assert dates == ["2026-03-17", "2026-03-16", "2026-03-15"]

    def test_empty_query_returns_empty(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-17.md": "# Wednesday, March 17 2026\n\nt buy milk",
        })
        results = search_vault("", vault)
        assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest tests/test_search.py -v`
Expected: FAIL — `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement `bujo/views/search.py`**

```python
"""Search view — search across all daily vault files.

Search is submit-based (not live). Results are generated by iterating
daily files and calling parse_entries on each.
"""

from datetime import date
from pathlib import Path

from textual.screen import Screen
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Input, Static, ListView, ListItem

from bujo.models import parse_entries
from bujo.vault import read_text_safe
from bujo.symbols import SYMBOL_DISPLAY, SYMBOL_COLORS


def search_vault(query: str, vault: Path) -> list[dict]:
    """Search all daily files for entries matching query.

    Returns list of dicts: {date, symbol, display, text, type}
    sorted newest first.
    """
    if not query.strip():
        return []

    query_lower = query.lower()
    daily = vault / "daily"
    if not daily.exists():
        return []

    results: list[dict] = []
    for f in sorted(daily.glob("*.md"), reverse=True):
        try:
            file_date = date.fromisoformat(f.stem)
        except ValueError:
            continue
        content = read_text_safe(f)
        entries = parse_entries(content, f, file_date)
        for entry in entries:
            if query_lower in entry.text.lower():
                results.append({
                    "date": file_date.isoformat(),
                    "symbol": entry.symbol,
                    "display": entry.display,
                    "text": entry.text,
                    "type": entry.type,
                })

    return results


class SearchView(Screen):
    """Inline search screen. / to open, Escape to close."""

    BINDINGS = [
        Binding("escape", "close_search", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="search-layout"):
            yield Input(placeholder="search entries...", id="search-input")
            yield ScrollableContainer(
                Static("[dim]type a query and press Enter[/dim]", id="search-status"),
                ListView(id="search-results"),
                id="search-scroll",
            )

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        from bujo.vault import VAULT
        query = event.value.strip()
        results = search_vault(query, VAULT)

        lv = self.query_one("#search-results", ListView)
        lv.clear()
        status = self.query_one("#search-status", Static)

        if not results:
            status.update(f'[dim]no results for "{query}"[/dim]')
            return

        status.update(f"[dim]{len(results)} result{'s' if len(results) != 1 else ''}[/dim]")
        for r in results:
            display = SYMBOL_DISPLAY.get(r["symbol"], r["symbol"])
            color = SYMBOL_COLORS.get(r["symbol"], "white")
            label = f"[dim]{r['date']}[/dim]  [{color}]{display}[/] {r['text']}  [dim italic]{r['type']}[/dim italic]"
            lv.append(ListItem(Static(label)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Jump to selected day when a search result is picked."""
        # Results store date in the label text; extract it
        item = event.item
        label = item.children[0].renderable if item.children else ""
        label_str = str(label)
        # Date is the first 10 chars after [dim] markup
        import re
        match = re.search(r"(\d{4}-\d{2}-\d{2})", label_str)
        if match:
            from datetime import date as dt_date
            target = dt_date.fromisoformat(match.group(1))
            self.dismiss(target)  # Return the date to DailyView

    def action_close_search(self) -> None:
        self.app.pop_screen()
```

- [ ] **Step 4: Run tests**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest tests/test_search.py -v`
Expected: ALL pass

- [ ] **Step 5: Commit**

```bash
git add bujo/views/search.py tests/test_search.py
git commit -m "feat: add vault-wide search with submit-based results"
```

---

## Task 11: Rebuild `views/daily.py` — The Redesigned DailyView

This is the core of the redesign. The new DailyView has no modes — just focus-based interaction.

**Files:**
- Create: `bujo/views/daily.py`
- Modify: `bujo/app.py` (replace DailyView import)

- [ ] **Step 1: Create `bujo/views/daily.py`**

Build the new DailyView with these behaviors:
- Always launches with input focused (no mode detection)
- Uses `BuJoInput` (arrow-up transfers to list)
- Uses `BuJoListView` (arrow-down at bottom transfers to input)
- Uses `DateRibbon` for day navigation
- Enter key disambiguation via focus checking
- Inline editing via `EntryItem.start_edit()`
- Undo via `UndoStack`
- Hints via `HintManager`
- `[` / `]` for date navigation
- `/` to push SearchView
- `x` / `k` / `>` for status changes (only when list has focus, not editing)
- `m` / `f` / `M` / `?` for secondary screens
- Ctrl+B for coach, Ctrl+D for dump mode
- `thinking...` indicator when AI is parsing (run AI call in a Textual worker via `self.run_worker()` to avoid blocking the TUI)
- After submitting an entry while viewing a past day, auto-switch to today so the user sees their entry
- Save confirmation via `.entry-new` CSS class
- Status change feedback via `self.notify()`
- Past-day indicator replaces greeting when not viewing today
- Empty state: `no entries yet` or `no entries on this day`

This file will be ~300-400 lines. The key structural difference from the old DailyView:
- No `nav_mode` reactive
- No `_update_prompt()` mode switching
- Focus-based dispatch for all key handling

**Implementation approach:** Start from scratch rather than modifying the old DailyView. The interaction model is fundamentally different. Copy patterns (coach, dump mode) from the old code but wire them into the new focus-based system.

The full implementation is too long to include inline here — the developer should:
1. Read the spec Section 1 (interaction model) carefully
2. Read the old `DailyView` in `app.py` (lines 495-1090) for patterns to preserve (coach, dump, first-run)
3. Build the new DailyView composing: `DateRibbon`, `BuJoListView`, `BuJoInput`
4. Wire undo, hints, search, and visual feedback

Key code patterns to follow:

```python
# Enter key disambiguation
def action_submit(self) -> None:
    # Check which widget has focus
    inp = self.query_one("#main-input", BuJoInput)
    if inp.has_focus:
        self._submit_new_entry()
        return

    lv = self.query_one("#entry-list", BuJoListView)
    if lv.has_focus:
        highlighted = lv.highlighted_child
        if highlighted and isinstance(highlighted, EntryItem):
            if highlighted.is_editing:
                return  # Input.Submitted handles this
            highlighted.start_edit()

# Status changes — only when list has focus and not editing
def on_key(self, event: events.Key) -> None:
    lv = self.query_one("#entry-list", BuJoListView)
    if not lv.has_focus:
        return
    highlighted = lv.highlighted_child
    if highlighted and isinstance(highlighted, EntryItem) and highlighted.is_editing:
        return  # Don't intercept keys during inline edit

    if event.key == "x":
        self._mark_done()
        event.stop()
    elif event.key == "k":
        self._kill_entry()
        event.stop()
    # ... etc
```

- [ ] **Step 2: Update `bujo/app.py`**

Replace the old `DailyView` import/class with:
```python
from bujo.views.daily import DailyView
```

Remove the entire old `DailyView` class, `BuJoListView`, `EntryItem`, and `_format_entry` from `app.py`.

- [ ] **Step 3: Manual smoke test**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m bujo.cli`

Verify:
- App launches with cursor in input area
- Type text, Enter saves
- Arrow up moves to entry list
- Enter on entry starts inline edit
- Escape cancels edit
- `[` / `]` navigate days
- `/` opens search
- Ctrl+Z undoes last action
- `x` / `k` / `>` work on highlighted entries
- m/f/M/?/Ctrl+B/Ctrl+D still work

- [ ] **Step 4: Run all tests**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest -v`
Expected: ALL pass. CLI tests don't test TUI behavior. Model/capture/analytics tests are unchanged.

- [ ] **Step 5: Commit**

```bash
git add bujo/views/daily.py bujo/app.py
git commit -m "feat: rebuild DailyView with modeless interaction model"
```

---

## Task 12: Slim Down `app.py` and Add CSS

**Files:**
- Modify: `bujo/app.py` (final slim version)
- Modify: `bujo/app.tcss` (add new styles)

- [ ] **Step 1: Final `bujo/app.py`**

`app.py` should now contain only:
- Imports and re-exports from `bujo.symbols` and `bujo.vault`
- `BuJoApp` class (~15 lines)
- `main()` function

```python
"""BuJo Textual TUI application."""

from textual.app import App
from textual.binding import Binding

# Re-exports for backward compatibility (existing tests import from bujo.app)
from bujo.symbols import *  # noqa: F401,F403
from bujo.vault import *    # noqa: F401,F403

from bujo.views.daily import DailyView


class BuJoApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "BuJo"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        from bujo.vault import ensure_vault
        ensure_vault()
        self.push_screen(DailyView())


def main() -> None:
    from bujo.vault import ensure_vault
    ensure_vault()
    app = BuJoApp()
    app.run(headless=False, size=(80, 24))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add CSS for new features to `bujo/app.tcss`**

Append to existing CSS:

```css
/* ── Date ribbon ──────────────────────────────── */

#date-ribbon {
    height: 1;
    color: $text-muted;
    padding: 0 2;
}

/* ── Past-day indicator ───────────────────────── */

#past-day-indicator {
    height: 1;
    color: $warning;
    padding: 0 2;
}

/* ── New entry highlight ──────────────────────── */

.entry-new {
    background: $primary-darken-2;
}

/* ── Inline edit ──────────────────────────────── */

#inline-edit {
    height: 1;
    border: none;
    background: $surface;
    padding: 0;
    margin: 0;
}

/* ── Search ───────────────────────────────────── */

#search-layout {
    height: 100%;
}

#search-input {
    height: 1;
    border: none;
    padding: 0 2;
    margin: 0;
}

#search-scroll {
    height: 1fr;
    padding: 0 2;
    border: none;
}

#search-status {
    height: 1;
    color: $text-disabled;
    padding: 0 0;
}

#search-results {
    height: auto;
    background: transparent;
}
```

- [ ] **Step 3: Run all tests**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest -v`
Expected: ALL pass

- [ ] **Step 4: Commit**

```bash
git add bujo/app.py bujo/app.tcss
git commit -m "refactor: slim app.py to launcher with re-exports, add CSS for new features"
```

---

## Task 13: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `cd C:\Users\User\Desktop\Bujo\bujo-ai && python -m pytest -v --tb=short`
Expected: ALL tests pass

- [ ] **Step 2: Manual end-to-end test**

Launch the TUI and verify every feature from the spec:
1. Cursor starts in input area (always, even with existing entries)
2. Type `buy milk`, Enter — saved, AI classifies, entry appears with type label
3. Type `t call Jackson`, Enter — prefix detected, saved immediately as task
4. Arrow up — focus moves to entry list
5. Arrow down at bottom — focus returns to input
6. Enter on entry — inline edit starts
7. Edit text, Enter — saved
8. Escape during edit — cancelled
9. `x` on entry — marked done with feedback
10. Ctrl+Z — undo works
11. `[` — navigate to yesterday
12. See `viewing Mar 16 · typing saves to today` indicator
13. Type something, Enter — auto-switches to today
14. `/` — search opens, type query, Enter, results appear
15. Ctrl+B — coach works
16. `?` — help screen shows updated keybindings
17. `m` / `f` / `M` — secondary screens work
18. Ctrl+D — dump mode works

- [ ] **Step 3: Run CLI commands**

```bash
bujo log
bujo coach --human
bujo week
bujo streak
bujo vault
bujo add t "test from cli"
bujo capture "feeling good today"
```
Expected: All CLI commands work exactly as before.

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address issues found during final verification"
```

---

## Dependency Order

```
Task 1 (symbols.py)
  └─> Task 2 (vault.py)
        └─> Task 3 (debug cleanup)
              └─> Task 9 (extract secondary views)
                    └─> Task 11 (daily.py) ─── requires all below:

Task 4 (undo.py) ──────────────────────────────┐
Task 5 (hints.py) ─────────────────────────────├─> Task 11 (daily.py)
Task 6 (input_bar.py) ─────────────────────────┤
Task 7 (entry_list.py) ────────────────────────┤
Task 8 (date_ribbon.py + widget tests) ────────┤
Task 9 └─> Task 10 (search.py) ───────────────┘

Task 11 (daily.py)
  └─> Task 12 (slim app.py + CSS)
        └─> Task 13 (verification)
```

Tasks 4-8 and 10 are independent of each other and can be done in parallel.
Tasks 1-3 must be sequential.
Task 9 depends on Tasks 1-2 (for imports). Task 10 depends on Task 9 (needs `bujo/views/` directory).
Task 11 depends on everything above.
Tasks 12-13 are sequential at the end.
