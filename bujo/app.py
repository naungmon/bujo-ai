"""BuJo Textual TUI application."""

import sys
import os
import subprocess
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, ListView, ListItem
from textual.containers import Container, Vertical, ScrollableContainer
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from textual import events, on, work
from datetime import date

VAULT = Path(os.environ.get("BUJO_VAULT", Path.home() / "bujo-vault"))
DAILY = VAULT / "daily"
FUTURE = VAULT / "future"
MONTHLY = VAULT / "monthly"
REFLECTIONS = VAULT / "reflections"

SYMBOLS = {
    "t": ("Task", "Something to do"),
    "x": ("Done", "Completed"),
    ">": ("Migrated", "Moved forward"),
    "k": ("Killed", "Consciously dropped"),
    "n": ("Note", "Thought or observation"),
    "e": ("Event", "Happened or scheduled"),
    "*": ("Priority", "This one matters today"),
}

SYMBOL_DISPLAY = {
    "t": "\u00b7",  # · task
    "x": "\u00d7",  # × done
    ">": ">",  # > migrated
    "k": "~",  # ~ killed
    "n": "\u2013",  # – note
    "e": "\u25cb",  # ○ event
    "*": "\u2605",  # ★ priority
}


def open_in_editor(path: Path | str) -> None:
    """Open a file in the user's preferred editor, cross-platform."""
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        editor = "notepad" if sys.platform == "win32" else "nano"
    try:
        subprocess.run([editor, str(path)], check=False)
    except FileNotFoundError:
        pass


def ensure_vault() -> None:
    """Create vault directories if they don't exist."""
    for d in [DAILY, FUTURE, MONTHLY, REFLECTIONS]:
        d.mkdir(parents=True, exist_ok=True)


def today_path() -> Path:
    """Return path to today's daily log file."""
    return DAILY / f"{date.today().isoformat()}.md"


def read_text_safe(path: Path) -> str:
    """Read text file with UTF-8, falling back to cp1252 for legacy files."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")


def today_log() -> str:
    """Read today's log, creating it if needed."""
    p = today_path()
    if not p.exists():
        header = f"# {date.today().strftime('%A, %B %d %Y')}\n\n"
        p.write_text(header, encoding="utf-8")
    return read_text_safe(p)


def save_today(content: str) -> None:
    """Write content to today's log file."""
    today_path().write_text(content, encoding="utf-8")


def append_entry(symbol: str, text: str) -> None:
    """Append a new entry to today's log.

    Writes ASCII symbol to file (t, x, >, k, n, e, *).
    """
    p = today_path()
    if not p.exists():
        today_log()  # creates the file with header
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"{symbol} {text}\n")


def parse_entries(content: str) -> list[dict]:
    """Parse log content into a list of entry dicts.

    Handles both ASCII format (t, x, >, k, n, e, *)
    and legacy Unicode (·, ×, >, ~, –, ○, ★).
    """
    entries: list[dict] = []

    # Build prefix -> symbol mapping for both ASCII and Unicode
    prefix_to_sym: dict[str, str] = {}
    for sym in SYMBOLS:
        prefix_to_sym[sym] = sym
    for display, sym in SYMBOL_DISPLAY.items():
        prefix_to_sym[display] = sym

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for prefix, sym in prefix_to_sym.items():
            if stripped.startswith(prefix + " "):
                text = stripped[len(prefix) + 1 :].strip()
                name, _ = SYMBOLS.get(sym, ("Unknown", ""))
                display = SYMBOL_DISPLAY.get(sym, prefix)
                entries.append(
                    {
                        "symbol": sym,
                        "display": display,
                        "text": text,
                        "type": name,
                        "raw": stripped,
                    }
                )
                break
    return entries


def get_monthly_path() -> Path:
    """Return path to current month's file."""
    return MONTHLY / f"{date.today().strftime('%Y-%m')}.md"


def get_future_path() -> Path:
    """Return path to future log."""
    return FUTURE / "future.md"


def get_all_logs_summary() -> str:
    """Return structured summary of recent logs for /bujo slash command."""
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


class EntryItem(ListItem):
    """A single entry in a ListView."""

    def __init__(self, entry: dict, index: int) -> None:
        super().__init__()
        self.entry = entry
        self.index = index

    def compose(self) -> ComposeResult:
        sym = self.entry["display"]
        text = self.entry["text"]
        etype = self.entry["type"]
        color_map = {
            "t": "cyan",
            "x": "green",
            ">": "blue",
            "k": "dim",
            "n": "yellow",
            "e": "magenta",
            "*": "red",
        }
        color = color_map.get(self.entry["symbol"], "white")
        yield Static(
            f"[bold {color}]{sym}[/bold {color}]  [white]{text}[/white]  [dim]{etype}[/dim]"
        )


class HelpScreen(ModalScreen):
    """Modal showing all keybindings."""

    BINDINGS = [Binding("escape,q", "app.pop_screen", "Close")]

    def compose(self) -> ComposeResult:
        with Container(id="help-box"):
            yield Static("[bold]BuJo \u2014 Keyboard Shortcuts[/bold]\n", markup=True)
            yield Static(
                "[bold]-- Adding entries --[/bold]\n"
                "[cyan]a[/cyan]  Open add entry (type freely)\n\n"
                "[bold]-- When an entry is selected --[/bold]\n"
                "[cyan]t[/cyan]  Retype as \u00b7 Task\n"
                "[green]x[/green]  Retype as \u00d7 Done\n"
                "[blue]>[/blue]  Retype as > Migrated\n"
                "[dim]k[/dim]  Retype as ~ Killed\n"
                "[yellow]n[/yellow]  Retype as \u2013 Note\n"
                "[magenta]e[/magenta]  Retype as \u25cb Event\n"
                "[red]*[/red]  Retype as \u2605 Priority\n\n"
                "[bold]-- Navigation --[/bold]\n"
                "[white]\u2191 \u2193[/white]  Select entry\n"
                "[white]m[/white]  Monthly log\n"
                "[white]f[/white]  Future log\n"
                "[white]r[/white]  Reflections\n"
                "[white]M[/white]  Migration mode\n"
                "[white]i[/white]  Insights\n"
                "[white]Q[/white]  Quick capture\n"
                "[white]?[/white]  This help screen\n"
                "[white]d[/white]  Daily view\n\n"
                "[dim]Press Escape to close[/dim]",
                markup=True,
            )

    def on_mount(self) -> None:
        self.query_one("#help-box").focus()


class QuickEntryScreen(ModalScreen):
    """Modal for quick entry of a new item."""

    def __init__(self, symbol: str, symbol_name: str) -> None:
        super().__init__()
        self.symbol = symbol
        self.symbol_name = symbol_name

    def compose(self) -> ComposeResult:
        display = SYMBOL_DISPLAY.get(self.symbol, self.symbol)
        with Container(id="entry-box"):
            yield Static(f"[bold]{display} New {self.symbol_name}[/bold]", markup=True)
            yield Input(placeholder="What's on your mind...", id="entry-input")
            yield Static(
                "[dim]Enter to save \u00b7 Escape to cancel[/dim]", markup=True
            )

    def on_mount(self) -> None:
        self.query_one("#entry-input").focus()

    @on(Input.Submitted)
    def save_entry(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if text:
            append_entry(self.symbol, text)
        self.dismiss(bool(text))

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(False)


class AddEntryScreen(ModalScreen):
    """Type-first entry modal. Symbol auto-detected from text."""

    def compose(self) -> ComposeResult:
        with Container(id="add-box"):
            yield Input(placeholder="what's on your mind...", id="add-input")
            yield Static("", id="detected-type")
            yield Static(
                "[dim]t task  n note  e event  * priority  x done[/dim]",
                markup=True,
                id="override-hints",
            )
            yield Static("[dim]Enter save · Escape cancel[/dim]", markup=True)

    def on_mount(self) -> None:
        from bujo.capture import detect_type

        self.detected_symbol = "t"
        self.override = None
        self.query_one("#add-input").focus()

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        from bujo.capture import parse_quick_input

        if self.override is None:
            symbol, _ = parse_quick_input(event.value)
            self.detected_symbol = symbol
        self._update_label()

    def _update_label(self) -> None:
        sym = self.override or self.detected_symbol
        display = SYMBOL_DISPLAY.get(sym, sym)
        name = SYMBOLS.get(sym, ("Unknown", ""))[0]
        color_map = {
            "t": "cyan",
            "x": "green",
            ">": "blue",
            "k": "dim",
            "n": "yellow",
            "e": "magenta",
            "*": "red",
        }
        color = color_map.get(sym, "white")
        self.query_one("#detected-type", Static).update(
            f"[bold {color}]{display} {name}[/bold {color}]"
        )

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(False)
            return
        if event.key in ("t", "x", ">", "k", "n", "e", "*"):
            self.override = event.key
            self._update_label()
            event.stop()

    @on(Input.Submitted)
    def save_entry(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if text:
            sym = self.override or self.detected_symbol
            from bujo.capture import parse_quick_input

            _, cleaned = parse_quick_input(text)
            append_entry(sym, cleaned if self.override is None else text)
        self.dismiss(bool(text))


class MigrationScreen(Screen):
    """Screen for monthly migration of pending tasks."""

    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding(">", "migrate", "Keep/Migrate"),
        Binding("d", "kill", "Kill"),
        Binding("f", "to_future", "Future Log"),
        Binding("j", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="migration-container"):
            yield Static(
                "[bold]Migration Mode[/bold]  [dim]Review unfinished tasks[/dim]\n",
                markup=True,
                id="mig-header",
            )
            yield Static("", id="mig-question")
            yield ListView(id="mig-list")
            yield Static(
                "\n[cyan]>[/cyan] migrate  [red]d[/red] kill  [blue]f[/blue] future log  [dim]\u2191\u2193 navigate[/dim]",
                markup=True,
                id="mig-actions",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.pending: list[dict] = []
        self.load_pending()

    def load_pending(self) -> None:
        lv = self.query_one("#mig-list", ListView)
        lv.clear()
        self.pending = []
        for f in sorted(DAILY.glob("*.md"), reverse=True)[:30]:
            try:
                content = read_text_safe(f)
            except (OSError, PermissionError):
                continue
            entries = parse_entries(content)
            for e in entries:
                if e["symbol"] == "t":
                    e["source_file"] = f
                    self.pending.append(e)

        if not self.pending:
            self.query_one("#mig-question", Static).update(
                "[green]No pending tasks. You're clean.[/green]"
            )
            return

        for i, e in enumerate(self.pending):
            lv.append(EntryItem(e, i))

        self.update_question()

    def update_question(self) -> None:
        if not self.pending:
            return
        self.query_one("#mig-question", Static).update(
            "[dim]Would you write this task again today?[/dim]"
        )

    def action_migrate(self) -> None:
        self._act_on_selected(">")

    def action_kill(self) -> None:
        self._act_on_selected("~")

    def action_to_future(self) -> None:
        lv = self.query_one("#mig-list", ListView)
        if lv.highlighted_child is None:
            return
        idx = lv.index
        if idx is None or idx >= len(self.pending):
            return
        entry = self.pending[idx]
        future = get_future_path()
        try:
            existing = read_text_safe(future) if future.exists() else "# Future Log\n\n"
        except (OSError, PermissionError):
            existing = "# Future Log\n\n"
        existing = existing.rstrip("\n") + f"\n> {entry['text']}\n"
        future.write_text(existing, encoding="utf-8")
        self._replace_in_source(entry, ">")
        lv.highlighted_child.remove()
        self.pending.pop(idx)

    def _act_on_selected(self, new_sym: str) -> None:
        lv = self.query_one("#mig-list", ListView)
        if lv.highlighted_child is None:
            return
        idx = lv.index
        if idx is None or idx >= len(self.pending):
            return
        entry = self.pending[idx]
        self._replace_in_source(entry, new_sym)
        lv.highlighted_child.remove()
        self.pending.pop(idx)

    def _replace_in_source(self, entry: dict, new_sym: str) -> None:
        f = entry["source_file"]
        try:
            content = read_text_safe(f)
        except (OSError, PermissionError):
            return
        old_line = entry["raw"]
        new_line = f"{new_sym} {entry['text']}"
        content = content.replace(old_line, new_line, 1)
        f.write_text(content, encoding="utf-8")

    def action_cursor_down(self) -> None:
        self.query_one("#mig-list", ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#mig-list", ListView).action_cursor_up()


class DailyView(Screen):
    """Main daily log view."""

    BINDINGS = [
        Binding("a", "add_entry", "Add"),
        Binding("e", "edit_raw", "Edit raw"),
        Binding("r", "reflection", "Reflect"),
        Binding("m", "monthly", "Monthly"),
        Binding("f", "future", "Future"),
        Binding("M", "migration", "Migrate all"),
        Binding("i", "insights", "Insights"),
        Binding("Q", "quick_capture", "Quick capture"),
        Binding("?", "help", "Help"),
        # Retype bindings (hidden, only work when entry selected)
        Binding("t", "retype_task", "Task", show=False),
        Binding("x", "retype_done", "Done", show=False),
        Binding(">", "retype_migrate", "Migrate", show=False),
        Binding("k", "retype_kill", "Kill", show=False),
        Binding("n", "retype_note", "Note", show=False),
        Binding("e", "retype_event", "Event", show=False),
        Binding("*", "retype_priority", "Priority", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="daily-layout"):
            yield Static("", id="date-label")
            yield Static("", id="entry-count")
            yield ScrollableContainer(
                ListView(id="entry-list"),
                id="entry-scroll",
            )
            yield Static(
                "[dim]a[/dim] add   [dim]select + t x > k n e *[/dim] retype   [dim]? help[/dim]",
                markup=True,
                id="hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_log()

    def refresh_log(self) -> None:
        from bujo.time import session_greeting
        from bujo.analytics import InsightsEngine

        content = today_log()
        entries = parse_entries(content)
        done = sum(1 for e in entries if e["symbol"] == "x")
        pending = sum(1 for e in entries if e["symbol"] == "t")
        priority = sum(1 for e in entries if e["symbol"] == "*")

        engine = InsightsEngine(VAULT)
        s = engine.streak()

        greeting = session_greeting(streak=s, pending_count=pending)
        self.query_one("#date-label", Static).update(f"[bold]{greeting}[/bold]")
        lv = self.query_one("#entry-list", ListView)
        lv.clear()

        if not entries:
            self.query_one("#entry-count", Static).update(
                "[dim]No entries yet today[/dim]"
            )
            self.query_one("#entry-list", ListView).mount(
                Static(
                    "[dim]Press a to add \u00b7 type naturally \u00b7 auto-detects symbol[/dim]"
                )
            )
            return

        for i, e in enumerate(entries):
            lv.append(EntryItem(e, i))

        done = sum(1 for e in entries if e["symbol"] == "x")
        pending = sum(1 for e in entries if e["symbol"] == "t")
        priority = sum(1 for e in entries if e["symbol"] == "*")
        self.query_one("#entry-count", Static).update(
            f"[green]{done} done[/green]  [cyan]{pending} pending[/cyan]  [red]{priority} priority[/red]"
        )

    @work(thread=True)
    def action_add_entry(self) -> None:
        saved = self.app.push_screen_wait(AddEntryScreen())
        if saved:
            self.app.call_from_thread(self.refresh_log)

    def _retype_selected(self, new_symbol: str) -> None:
        """Change the type of the currently highlighted entry."""
        lv = self.query_one("#entry-list", ListView)
        if lv.highlighted_child is None:
            return
        idx = lv.index
        entries = parse_entries(today_log())
        if idx is None or idx >= len(entries):
            return
        entry = entries[idx]
        content = today_log()
        new_line = f"{new_symbol} {entry['text']}"
        content = content.replace(entry["raw"], new_line, 1)
        save_today(content)
        self.refresh_log()

    def action_retype_task(self) -> None:
        self._retype_selected("t")

    def action_retype_done(self) -> None:
        self._retype_selected("x")

    def action_retype_migrate(self) -> None:
        self._retype_selected(">")

    def action_retype_kill(self) -> None:
        self._retype_selected("k")

    def action_retype_note(self) -> None:
        self._retype_selected("n")

    def action_retype_event(self) -> None:
        self._retype_selected("e")

    def action_retype_priority(self) -> None:
        self._retype_selected("*")

    def action_edit_raw(self) -> None:
        open_in_editor(today_path())
        self.refresh_log()

    def action_reflection(self) -> None:
        self.app.push_screen(ReflectionView())

    def action_monthly(self) -> None:
        self.app.push_screen(MonthlyView())

    def action_future(self) -> None:
        self.app.push_screen(FutureView())

    def action_migration(self) -> None:
        self.app.push_screen(MigrationScreen())

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_insights(self) -> None:
        self.app.push_screen(InsightsView())

    def action_quick_capture(self) -> None:
        self.app.push_screen(AddEntryScreen())


class QuickCaptureScreen(ModalScreen):
    """Modal for NLP-powered quick capture (same as AddEntryScreen)."""

    def compose(self) -> ComposeResult:
        with Container(id="add-box"):
            yield Input(placeholder="Capture anything...", id="add-input")
            yield Static("", id="detected-type")
            yield Static(
                "[dim]t task  n note  e event  * priority  x done[/dim]",
                markup=True,
                id="override-hints",
            )
            yield Static("[dim]Enter save · Escape cancel[/dim]", markup=True)

    def on_mount(self) -> None:
        self.detected_symbol = "t"
        self.override = None
        self.query_one("#add-input").focus()

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        from bujo.capture import parse_quick_input

        if self.override is None:
            symbol, _ = parse_quick_input(event.value)
            self.detected_symbol = symbol
        self._update_label()

    def _update_label(self) -> None:
        sym = self.override or self.detected_symbol
        display = SYMBOL_DISPLAY.get(sym, sym)
        name = SYMBOLS.get(sym, ("Unknown", ""))[0]
        color_map = {
            "t": "cyan",
            "x": "green",
            ">": "blue",
            "k": "dim",
            "n": "yellow",
            "e": "magenta",
            "*": "red",
        }
        color = color_map.get(sym, "white")
        self.query_one("#detected-type", Static).update(
            f"[bold {color}]{display} {name}[/bold {color}]"
        )

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(False)
            return
        if event.key in ("t", "x", ">", "k", "n", "e", "*"):
            self.override = event.key
            self._update_label()
            event.stop()

    @on(Input.Submitted)
    def save_entry(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if text:
            sym = self.override or self.detected_symbol
            from bujo.capture import parse_quick_input

            _, cleaned = parse_quick_input(text)
            append_entry(sym, cleaned if self.override is None else text)
        self.dismiss(bool(text))


class InsightsView(Screen):
    """Analytics dashboard showing patterns and insights."""

    BINDINGS = [Binding("escape,q", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="insights-layout"):
            yield Static("[bold]Insights[/bold]", markup=True)
            yield ScrollableContainer(
                Static("", id="insights-content"),
                id="insights-scroll",
            )
            yield Static("[dim]q back[/dim]", markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self.refresh()

    def refresh(self, *args, **kwargs) -> None:
        from bujo.analytics import InsightsEngine

        engine = InsightsEngine(VAULT)
        report = engine.full_report()

        if report["empty"]:
            self.query_one("#insights-content", Static).update(
                "[dim]Not enough data yet.\n"
                "Keep logging for a few days and patterns will appear.\n\n"
                "Try: bujo template morning[/dim]"
            )
            return

        momentum = report["momentum"]
        streak = report["streak"]
        completion = report["completion_rate_7d"]
        alignment = report["priority_alignment_7d"]
        nudge = report["nudge"]

        momentum_bar = {
            "building": "[green]\u2588\u2588\u2588\u2588\u2589\u2589[/green] building",
            "steady": "[cyan]\u2588\u2588\u2588\u2588\u2588[/cyan] steady",
            "stalling": "[yellow]\u2588\u2588\u2588\u2589\u2589[/yellow] stalling",
            "stalled": "[red]\u2588\u2588\u2589\u2589\u2589[/red] stalled",
            "new": "[dim]\u2589\u2589\u2589\u2589\u2589[/dim] new",
        }.get(momentum, momentum)

        lines = [
            f"Momentum    {momentum_bar}",
            f"Streak      \U0001f525 {streak} day{'s' if streak != 1 else ''}",
            f"This week   {completion:.0%} completion",
            f"Priorities  {alignment:.0%} aligned",
            "",
        ]

        stuck = report["stuck_tasks"]
        if stuck:
            lines.append("[bold]-- Stuck tasks --[/bold]")
            for t in stuck[:3]:
                lines.append(f"  \u00b7 {t['text']}  ({t['count']}x)")
            lines.append("")

        themes = report["kill_themes"]
        if themes:
            lines.append("[bold]-- You tend to drop --[/bold]")
            theme_str = "  ".join(f"{k} ({v})" for k, v in list(themes.items())[:3])
            lines.append(f"  {theme_str}")
            lines.append("")

        lines.append("[bold]-- Today's nudge --[/bold]")
        lines.append(f"[italic]{nudge}[/italic]")

        self.query_one("#insights-content", Static).update("\n".join(lines))


class MonthlyView(Screen):
    """Monthly priorities view."""

    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding("a", "add_priority", "Add priority"),
        Binding("e", "edit_raw", "Edit raw"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="monthly-layout"):
            yield Static("", id="month-label")
            yield ScrollableContainer(
                Static("", id="monthly-content"),
                id="monthly-scroll",
            )
            yield Static(
                "[dim]a add priority  e edit raw  q back[/dim]",
                markup=True,
                id="m-hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh()

    def refresh(self, *args, **kwargs) -> None:
        month_str = date.today().strftime("%B %Y")
        self.query_one("#month-label", Static).update(f"[bold]{month_str}[/bold]")
        p = get_monthly_path()
        if not p.exists():
            p.write_text(f"# {month_str}\n\n## Priorities\n\n", encoding="utf-8")
        try:
            content = read_text_safe(p)
        except (OSError, PermissionError):
            content = "_(could not read file)_"
        self.query_one("#monthly-content", Static).update(content)

    @work(thread=True)
    def action_add_priority(self) -> None:
        saved = self.app.push_screen_wait(QuickEntryScreen("*", "Priority"))
        if saved:
            self.app.call_from_thread(self.refresh)

    def action_edit_raw(self) -> None:
        open_in_editor(get_monthly_path())
        self.refresh()


class FutureView(Screen):
    """Future log view for parked items."""

    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding("e", "edit_raw", "Edit raw"),
        Binding("a", "add_item", "Add item"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="future-layout"):
            yield Static("[bold]Future Log[/bold]", markup=True, id="future-label")
            yield ScrollableContainer(
                Static("", id="future-content"),
                id="future-scroll",
            )
            yield Static("[dim]a add  e edit raw  q back[/dim]", markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self.refresh()

    def refresh(self, *args, **kwargs) -> None:
        p = get_future_path()
        if not p.exists():
            p.write_text(
                "# Future Log\n\nThings parked for later. Not dead \u2014 just not now.\n\n",
                encoding="utf-8",
            )
        try:
            content = read_text_safe(p)
        except (OSError, PermissionError):
            content = "_(could not read file)_"
        self.query_one("#future-content", Static).update(content)

    def action_edit_raw(self) -> None:
        open_in_editor(get_future_path())
        self.refresh()

    @work(thread=True)
    def action_add_item(self) -> None:
        saved = self.app.push_screen_wait(QuickEntryScreen(".", "Future item"))
        if saved:
            self.app.call_from_thread(self.refresh)


class ReflectionView(Screen):
    """Reflections view for starred insights."""

    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding("e", "edit_raw", "Edit raw"),
        Binding("n", "new_reflection", "New"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="reflection-layout"):
            yield Static("[bold]Reflections[/bold]", markup=True)
            yield ScrollableContainer(
                Static("", id="reflection-content"),
                id="reflection-scroll",
            )
            yield Static("[dim]n new  e edit  q back[/dim]", markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self.refresh()

    def refresh(self, *args, **kwargs) -> None:
        files = sorted(REFLECTIONS.glob("*.md"), reverse=True)
        if not files:
            self.query_one("#reflection-content", Static).update(
                "[dim]No reflections yet. These are your starred (\u2013) entries worth keeping.\nPaste insights from your daily logs here.[/dim]"
            )
            return
        contents: list[str] = []
        for f in files[:5]:
            try:
                contents.append(read_text_safe(f))
            except (OSError, PermissionError):
                contents.append("_(could not read file)_")
        content = "\n\n---\n\n".join(contents)
        self.query_one("#reflection-content", Static).update(content)

    def action_new_reflection(self) -> None:
        p = REFLECTIONS / f"{date.today().isoformat()}.md"
        open_in_editor(p)
        self.refresh()

    def action_edit_raw(self) -> None:
        files = sorted(REFLECTIONS.glob("*.md"), reverse=True)
        if files:
            open_in_editor(files[0])
        self.refresh()


class BuJoApp(App):
    """Main BuJo Textual application."""

    CSS_PATH = "app.tcss"
    TITLE = "BuJo"
    SUB_TITLE = "ADHD-first bullet journal"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("d", "daily", "Daily"),
    ]

    def on_mount(self) -> None:
        ensure_vault()
        self.push_screen(DailyView())

    def action_daily(self) -> None:
        self.push_screen(DailyView())


def main() -> None:
    """Entry point for the TUI."""
    ensure_vault()
    app = BuJoApp()
    app.run()


if __name__ == "__main__":
    main()
