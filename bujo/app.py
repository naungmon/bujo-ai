"""BuJo Textual TUI application — redesigned interaction model."""

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, ListView, ListItem, Static, TextArea
from textual import events, on, work

from bujo.models import LogReader, parse_entries

VAULT = Path(os.environ.get("BUJO_VAULT", Path.home() / "bujo-vault"))
DAILY = VAULT / "daily"
FUTURE = VAULT / "future"
MONTHLY = VAULT / "monthly"
REFLECTIONS = VAULT / "reflections"
FIRST_RUN_FLAG = Path.home() / ".bujo-first-run-done"

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
    "t": "\u00b7",
    "x": "\u00d7",
    ">": ">",
    "k": "~",
    "n": "\u2013",
    "e": "\u25cb",
    "*": "\u2605",
}

SYMBOL_COLORS = {
    "t": "cyan",
    "x": "green",
    ">": "blue",
    "k": "dim",
    "n": "white",
    "e": "magenta",
    "*": "red",
}

# Navigation action symbols
NAV_ACTIONS = {"x": "x", "k": "k", ">": ">"}


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


def _format_entry(e) -> str:
    """Format an Entry object or dict as markup for ListView."""
    if hasattr(e, "symbol"):
        sym = e.symbol
        display = e.display
        text = e.text
        etype = e.type
    else:
        sym = e.get("symbol", "")
        display = e.get("display", "")
        text = e.get("text", "")
        etype = e.get("type", "")

    color = SYMBOL_COLORS.get(sym, "white")
    if sym == "x":
        return f"[{color} dim]{display}[/] [dim]{text}[/]  [dim italic]{etype}[/]"
    elif sym == "k":
        return f"[dim]{display}[/] [dim]{text}[/]  [dim italic]{etype}[/]"
    else:
        return f"[{color}]{display}[/] [white]{text}[/]  [dim italic]{etype}[/]"


class EntryItem(ListItem):
    def __init__(self, entry, index: int) -> None:
        super().__init__()
        self.entry = entry
        self.index = index

    def compose(self) -> ComposeResult:
        yield Static(_format_entry(self.entry))


# ── Secondary Screens ──────────────────────────────────


class MonthlyView(Screen):
    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding("a", "add_priority", "Add"),
        Binding("e", "edit_raw", "Edit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="secondary-layout"):
            yield Static("", id="secondary-title")
            yield Static("\u2500" * 40, id="secondary-separator")
            yield ScrollableContainer(
                Static("", id="secondary-content"),
                id="secondary-scroll",
            )
            yield Static(
                "[dim italic]a add priority \u00b7 e edit in $EDITOR \u00b7 Escape back[/dim italic]",
                id="secondary-hints",
            )

    def on_mount(self) -> None:
        self.refresh()

    def refresh(self, *args, **kwargs) -> None:
        month_str = date.today().strftime("%B %Y")
        self.query_one("#secondary-title", Static).update(f"[bold]{month_str}[/bold]")
        p = get_monthly_path()
        if not p.exists():
            p.write_text(f"# {month_str}\n\n## Priorities\n\n", encoding="utf-8")
        try:
            content = read_text_safe(p)
        except (OSError, PermissionError):
            content = "_(could not read file)_"
        self.query_one("#secondary-content", Static).update(content)

    @on(Input.Submitted, "#add-input")
    def on_add_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if text:
            from bujo.capture import parse_quick_input

            sym, cleaned = parse_quick_input(text)
            append_entry(sym, cleaned)
        self.remove("#add-container")
        self.refresh()

    def action_add_priority(self) -> None:
        from textual.containers import Container

        container = Container(id="add-container")
        self.query_one("#secondary-layout").mount(
            Static("[dim]New priority:[/dim]", id="add-label"),
            Input(placeholder="priority...", id="add-input"),
            after=self.query_one("#secondary-hints"),
        )
        self.query_one("#add-input", Input).focus()

    def action_edit_raw(self) -> None:
        open_in_editor(get_monthly_path())
        self.refresh()


class FutureView(Screen):
    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding("a", "add_item", "Add"),
        Binding("e", "edit_raw", "Edit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="secondary-layout"):
            yield Static("[bold]Future Log[/bold]", id="secondary-title")
            yield Static("\u2500" * 40, id="secondary-separator")
            yield ScrollableContainer(
                Static("", id="secondary-content"),
                id="secondary-scroll",
            )
            yield Static(
                "[dim italic]a add \u00b7 e edit in $EDITOR \u00b7 Escape back[/dim italic]",
                id="secondary-hints",
            )

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
        self.query_one("#secondary-content", Static).update(content)

    @on(Input.Submitted, "#add-input")
    def on_add_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if text:
            append_entry(">", text)
        self.remove("#add-container")
        self.refresh()

    def action_add_item(self) -> None:
        self.query_one("#secondary-layout").mount(
            Static("[dim]New future item:[/dim]", id="add-label"),
            Input(placeholder="park for later...", id="add-input"),
            after=self.query_one("#secondary-hints"),
        )
        self.query_one("#add-input", Input).focus()

    def action_edit_raw(self) -> None:
        open_in_editor(get_future_path())
        self.refresh()


class MigrationScreen(Screen):
    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding(">", "keep", "Keep"),
        Binding("d", "kill", "Kill"),
        Binding("f", "to_future", "Future"),
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="secondary-layout"):
            yield Static("[bold]Migration[/bold]", id="secondary-title")
            yield Static("\u2500" * 40, id="secondary-separator")
            yield Static("", id="mig-status")
            yield ListView(id="mig-list")
            yield Static(
                "[dim italic]> keep \u00b7 d kill \u00b7 f future \u00b7 "
                "\u2191\u2193 navigate \u00b7 Escape done[/dim italic]",
                id="secondary-hints",
            )

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
            entries = parse_entries(content, f, date.today())
            for e in entries:
                if e.symbol == "t":
                    self.pending.append(
                        {
                            "symbol": e.symbol,
                            "display": e.display,
                            "text": e.text,
                            "type": e.type,
                            "raw": e.raw,
                            "source_file": f,
                        }
                    )

        if not self.pending:
            self.query_one("#mig-status", Static).update(
                "[dim italic]no pending tasks. you're clean.[/dim italic]"
            )
            return

        count = len(self.pending)
        self.query_one("#mig-status", Static).update(
            f"[dim italic]{count} pending \u2014 "
            f"would you write this again today?[/dim italic]"
        )
        for i, e in enumerate(self.pending):
            lv.append(EntryItem(e, i))

    def _replace_in_source(self, entry: dict, new_sym: str) -> None:
        f = entry["source_file"]
        try:
            content = read_text_safe(f)
        except (OSError, PermissionError):
            return
        new_line = f"{new_sym} {entry['text']}"
        content = content.replace(entry["raw"], new_line, 1)
        f.write_text(content, encoding="utf-8")

    def _remove_selected(self) -> None:
        lv = self.query_one("#mig-list", ListView)
        if lv.highlighted_child is None:
            return
        idx = lv.index
        if idx is None or idx >= len(self.pending):
            return
        self.pending.pop(idx)
        lv.highlighted_child.remove()
        if not self.pending:
            self.query_one("#mig-status", Static).update(
                "[dim italic]no pending tasks. you're clean.[/dim italic]"
            )

    def action_keep(self) -> None:
        lv = self.query_one("#mig-list", ListView)
        if lv.highlighted_child is None or lv.index is None:
            return
        if lv.index >= len(self.pending):
            return
        self._replace_in_source(self.pending[lv.index], "t")
        self._remove_selected()

    def action_kill(self) -> None:
        lv = self.query_one("#mig-list", ListView)
        if lv.highlighted_child is None or lv.index is None:
            return
        if lv.index >= len(self.pending):
            return
        self._replace_in_source(self.pending[lv.index], "k")
        self._remove_selected()

    def action_to_future(self) -> None:
        lv = self.query_one("#mig-list", ListView)
        if lv.highlighted_child is None or lv.index is None:
            return
        if lv.index >= len(self.pending):
            return
        entry = self.pending[lv.index]
        future = get_future_path()
        try:
            existing = read_text_safe(future) if future.exists() else "# Future Log\n\n"
        except (OSError, PermissionError):
            existing = "# Future Log\n\n"
        existing = existing.rstrip("\n") + f"\n> {entry['text']}\n"
        future.write_text(existing, encoding="utf-8")
        self._replace_in_source(entry, ">")
        self._remove_selected()

    def action_cursor_down(self) -> None:
        self.query_one("#mig-list", ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#mig-list", ListView).action_cursor_up()


class HelpScreen(Screen):
    BINDINGS = [Binding("escape,q", "app.pop_screen", "Close")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="secondary-layout"):
            yield Static("[bold]BuJo \u2014 how it works[/bold]", id="secondary-title")
            yield Static("\u2500" * 40, id="secondary-separator")
            yield ScrollableContainer(
                Static(
                    "\n[dim italic]just type. prefix sets the type:[/dim italic]\n\n"
                    "[cyan]t[/cyan] or [cyan]task[/cyan]        \u00b7  task\n"
                    "[magenta]e[/magenta] or [magenta]event[/magenta]       \u25cb  event\n"
                    "[white]n[/white] or [white]note[/white]         \u2013  note\n"
                    "[red]*[/red] or [red]priority[/red]    \u2605  priority\n"
                    "[green]x[/green] or [green]done:[/green]       \u00d7  done\n"
                    "[dim]k[/dim] or [dim]kill:[/dim]         ~  killed\n"
                    "[blue]>[/blue]                  >  migrated\n"
                    "[dim italic](no prefix)        \u2013  note[/dim italic]\n\n"
                    "[dim italic]add ! to the end of anything \u2192 priority[/dim italic]\n\n"
                    "\u2500" * 40 + "\n\n"
                    "[dim italic]navigation[/dim italic]  (Escape to enter, Escape to exit)\n"
                    "  \u2191 \u2193    move through entries\n"
                    "  x      mark done\n"
                    "  k      kill\n"
                    "  >      migrate\n"
                    "  r      retype (edit and re-save)\n\n"
                    "[dim italic]views[/dim italic]\n"
                    "  m          monthly log\n"
                    "  f          future log\n"
                    "  M          migration pass\n"
                    "  Ctrl+B     coach\n"
                    "  ?          this screen\n"
                    "  q          quit\n",
                    markup=True,
                ),
            )
            yield Static(
                "[dim italic]Escape to close[/dim italic]",
                id="secondary-hints",
            )


# ── DailyView ──────────────────────────────────────────


class DailyView(Screen):
    """Main daily log with always-on input bar."""

    nav_mode = reactive(False)
    dump_mode = reactive(False)

    BINDINGS = [
        Binding("ctrl+b", "coach", "Coach"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="daily-layout"):
            yield Static("", id="date-label")
            yield Static("", id="greeting-label")
            yield Static("", id="count-label")
            yield Static("\u2500" * 48, id="separator")
            yield ScrollableContainer(
                Static(
                    "[dim italic]just start typing[/dim italic]",
                    id="empty-hint",
                ),
                ListView(id="entry-list"),
                id="entry-scroll",
            )
            yield Static("", id="inline-display")
            yield Static("", id="hint-bar")
            # Manual input bar (no Input widget — keys handled directly)
            yield Static("", id="input-bar")
            # Dump mode (hidden initially)
            yield Static(
                "[dim italic]dump mode[/dim italic]", id="dump-label", display=False
            )
            yield TextArea(id="dump-input", display=False)

    def on_mount(self) -> None:
        self._current_coach_mode = False
        self._input_text = ""
        self.refresh_log()

    def refresh_log(self) -> None:
        from bujo.analytics import InsightsEngine
        from bujo.time import session_greeting

        content = today_log()
        entries = parse_entries(content, today_path(), date.today())

        done = sum(1 for e in entries if e.symbol == "x")
        pending = sum(1 for e in entries if e.symbol == "t")
        priority = sum(1 for e in entries if e.symbol == "*")

        engine = InsightsEngine(VAULT)
        s = engine.streak()

        greeting = session_greeting(streak=s, pending_count=pending)
        self.query_one("#date-label", Static).update(
            f"[bold]{date.today().strftime('%A, %B %d %Y')}[/bold]"
        )
        self.query_one("#greeting-label", Static).update(f"{greeting}")

        lv = self.query_one("#entry-list", ListView)
        lv.clear()

        empty_hint = self.query_one("#empty-hint", Static)
        inline = self.query_one("#inline-display", Static)

        # Hide inline coach display
        inline.update("")
        inline.display = False

        if not entries:
            empty_hint.display = True
            lv.display = False
            self.query_one("#count-label", Static).update(
                "[dim italic]no entries yet[/dim italic]"
            )
            # Session detection: empty → input mode
            self.nav_mode = False
        else:
            empty_hint.display = False
            lv.display = True
            for i, e in enumerate(entries):
                lv.append(
                    EntryItem(
                        {
                            "symbol": e.symbol,
                            "display": e.display,
                            "text": e.text,
                            "type": e.type,
                            "raw": e.raw,
                        },
                        i,
                    )
                )
            self.query_one("#count-label", Static).update(
                f"[dim]{done} done[/dim]  [dim]\u00b7[/dim]  "
                f"[dim]{pending} pending[/dim]  [dim]\u00b7[/dim]  "
                f"[dim]{priority} priority[/dim]"
            )
            # Session detection: entries exist → nav mode
            self.nav_mode = True

        # First-run check
        if not FIRST_RUN_FLAG.exists() and not has_any_daily_files():
            self._show_first_run()
        else:
            self._hide_first_run()

        self._update_hint_bar()

    def _show_first_run(self) -> None:
        greeting = self.query_one("#greeting-label", Static)
        greeting.update(
            "[bold]BuJo \u2014 your ADHD journal[/bold]\n\n"
            f"[dim]vault ready at {VAULT}[/dim]\n\n"
            "[dim]just start typing. prefix is optional:[/dim]\n"
            "[cyan]t[/cyan] or [cyan]task[/cyan]      \u2192 task\n"
            "[magenta]e[/magenta] or [magenta]event[/magenta]     \u2192 event\n"
            "[white]n[/white] or [white]note[/white]      \u2192 note\n"
            "[red]*[/red] or [red]priority[/red]  \u2192 priority\n"
            "[dim italic](no prefix)      \u2192 note[/dim italic]\n\n"
            "[dim]anything with ! at the end becomes a priority.[/dim]"
        )

    def _hide_first_run(self) -> None:
        pass  # greeting is set by refresh_log

    def _set_input_focus(self) -> None:
        self._update_input_display()

    def _set_nav_focus_last(self) -> None:
        lv = self.query_one("#entry-list", ListView)
        if lv.children:
            lv.focus()
            # Move to last entry
            lv.index = len(lv.children) - 1

    def _update_input_display(self) -> None:
        bar = self.query_one("#input-bar", Static)
        if self.nav_mode:
            bar.update(f"[dim]\u25b8[/dim] [dim]{self._input_text}[/dim]")
        else:
            bar.update(f"[bold cyan]\u25b8[/bold cyan] {self._input_text}")

    def _update_hint_bar(self) -> None:
        hint = self.query_one("#hint-bar", Static)
        self._update_input_display()
        if self.nav_mode:
            hint.update(
                "[dim italic][nav][/dim italic]  "
                "[dim]\u2191\u2193 move[/dim]  "
                "[dim]x done[/dim]  "
                "[dim]k kill[/dim]  "
                "[dim]> migrate[/dim]  "
                "[dim]r retype[/dim]  "
                "[dim]Escape back[/dim]"
            )
        else:
            hint.update(
                "[dim italic][input][/dim italic]  "
                "[dim]Ctrl+B coach[/dim]  "
                "[dim]m monthly[/dim]  "
                "[dim]f future[/dim]  "
                "[dim]M migrate[/dim]  "
                "[dim]? help[/dim]  "
                "[dim]q quit[/dim]"
            )

    def watch_nav_mode(self, value: bool) -> None:
        self._update_hint_bar()

    def _get_selected_entry(self) -> dict | None:
        lv = self.query_one("#entry-list", ListView)
        if lv.highlighted_child is None or lv.index is None:
            return None
        entries = parse_entries(today_log(), today_path(), date.today())
        if lv.index >= len(entries):
            return None
        e = entries[lv.index]
        return {"symbol": e.symbol, "text": e.text, "raw": e.raw, "type": e.type}

    def _rewrite_entry(self, old_raw: str, new_sym: str, text: str) -> None:
        content = today_log()
        new_line = f"{new_sym} {text}"
        content = content.replace(old_raw, new_line, 1)
        save_today(content)

    def action_mark_done(self) -> None:
        if not self.nav_mode:
            return
        entry = self._get_selected_entry()
        if entry is None:
            return
        self._rewrite_entry(entry["raw"], "x", entry["text"])
        self.refresh_log()

    def action_kill_entry(self) -> None:
        if not self.nav_mode:
            return
        entry = self._get_selected_entry()
        if entry is None:
            return
        self._rewrite_entry(entry["raw"], "k", entry["text"])
        self.refresh_log()

    def action_migrate_entry(self) -> None:
        if not self.nav_mode:
            return
        entry = self._get_selected_entry()
        if entry is None:
            return
        self._rewrite_entry(entry["raw"], ">", entry["text"])
        self.refresh_log()

    def action_retype_entry(self) -> None:
        if not self.nav_mode:
            return
        entry = self._get_selected_entry()
        if entry is None:
            return
        # Mark old as migrated
        self._rewrite_entry(entry["raw"], ">", entry["text"])
        # Pre-fill input with text
        self._input_text = entry["text"]
        # Switch to input mode
        self.nav_mode = False
        self._update_input_display()

    @work(thread=True)
    def action_coach(self) -> None:
        from bujo.analytics import InsightsEngine

        engine = InsightsEngine(VAULT)
        reader = LogReader(VAULT)
        all_logs = reader.load_all()
        total = sum(len(log.entries) for log in all_logs)

        self.app.call_from_thread(self._show_coach, engine, total)

    def _show_coach(self, engine, total: int) -> None:
        self._current_coach_mode = True
        self._previous_nav_mode = self.nav_mode

        inline = self.query_one("#inline-display", Static)
        lv = self.query_one("#entry-list", ListView)
        empty = self.query_one("#empty-hint", Static)

        # Hide list, show inline
        lv.display = False
        empty.display = False
        inline.display = True

        if total < 5:
            remaining = 5 - total
            inline.update(
                f"\n[dim italic]write {remaining} more entr{'y' if remaining == 1 else 'ies'} first.\n"
                f"i'll have something to say after 5.\n\n"
                f"you have {total} so far.[/dim italic]\n\n"
                f"[dim italic]any key to close[/dim italic]"
            )
        else:
            report = engine.full_report()
            lines = [
                "",
                "[dim italic]\u2500\u2500 coach \u2500\u2500\u2500\u2500\u2500\u2500"
                "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
                "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
                "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
                "\u2500\u2500\u2500\u2500\u2500\u2500\u2500[/dim italic]",
                "",
                f"  momentum      {report['momentum']}",
                f"  streak        {report['streak']} day{'s' if report['streak'] != 1 else ''}",
                f"  done today    {sum(1 for e in parse_entries(today_log(), today_path(), date.today()) if e.symbol == 'x')}",
                "",
            ]

            stuck = report.get("stuck_tasks", [])
            if stuck:
                lines.append("[dim italic]  stuck[/dim italic]")
                for t in stuck[:3]:
                    lines.append(
                        f"  \u00b7 {t['text']}  [dim]moved {t['count']} times[/dim]"
                    )
                lines.append("")

            themes = report.get("kill_themes", {})
            if themes:
                lines.append("[dim italic]  dropping[/dim italic]")
                for theme, count in list(themes.items())[:2]:
                    lines.append(f"  {theme} tasks  [dim]killed {count} times[/dim]")
                lines.append("")

            productive = report.get("most_productive_time", "not enough data")
            if "not enough" not in productive:
                lines.append("[dim italic]  most productive[/dim italic]")
                lines.append(f"  {productive}")
                lines.append("")

            lines.append("[dim italic]\u2500" * 48 + "[/dim italic]")
            lines.append("")
            lines.append(f"  [cyan]{report['nudge']}[/cyan]")
            lines.append("")
            lines.append("[dim italic]any key to close[/dim italic]")
            inline.update("\n".join(lines))

    def _close_coach(self) -> None:
        self._current_coach_mode = False
        inline = self.query_one("#inline-display", Static)
        inline.update("")
        inline.display = False
        self.refresh_log()

    def _submit_input(self) -> None:
        """Submit the current input buffer."""
        text = self._input_text.strip()
        self._input_text = ""
        self._update_input_display()

        if not text:
            # Empty submit: if not in nav mode, maybe switch to nav
            if not self.nav_mode:
                entries = parse_entries(today_log(), today_path(), date.today())
                if entries:
                    self.nav_mode = True
                    self._set_nav_focus_last()
            return

        from bujo.capture import parse_quick_input

        symbol, cleaned = parse_quick_input(text)
        append_entry(symbol, cleaned)

        # Write first-run flag
        if not FIRST_RUN_FLAG.exists():
            FIRST_RUN_FLAG.write_text("done\n", encoding="utf-8")

        self.refresh_log()

    def _enter_dump_mode(self) -> None:
        """Enter dump mode with multiline TextArea."""
        self.dump_mode = True
        # Hide input bar
        try:
            self.query_one("#input-bar", Static).display = False
        except Exception:
            pass
        # Show dump input area
        try:
            self.query_one("#dump-input", TextArea).display = True
            self.query_one("#dump-label", Static).display = True
            self.query_one("#dump-input", TextArea).focus()
        except Exception:
            pass
        self.query_one("#hint-bar", Static).update(
            "[dim italic][dump][/dim italic]  "
            "[dim]Ctrl+Enter save[/dim]  "
            "[dim]Escape cancel[/dim]"
        )

    def _exit_dump_mode(self) -> None:
        """Exit dump mode, restore normal input."""
        self.dump_mode = False
        # Hide dump input
        try:
            self.query_one("#dump-input", TextArea).display = False
            self.query_one("#dump-label", Static).display = False
        except Exception:
            pass
        self._update_input_display()
        self._update_hint_bar()

    @work(thread=True)
    def _submit_dump(self) -> None:
        """Submit dump text for AI parsing."""
        from bujo.ai import save_dump_and_parse, show_setup_instructions, get_ai_config
        from bujo.app import SYMBOL_DISPLAY

        try:
            text_area = self.query_one("#dump-input", TextArea)
            text = text_area.text
        except Exception:
            return

        if not text.strip():
            self.app.call_from_thread(self._exit_dump_mode)
            return

        # Show parsing indicator
        self.app.call_from_thread(
            lambda: self.query_one("#inline-display", Static).update(
                "[dim italic]parsing...[/dim italic]"
            )
        )
        self.app.call_from_thread(
            lambda: self.query_one("#inline-display", Static).update("")
        )

        success, entries, err = save_dump_and_parse(text, VAULT)

        if success:
            # Show results briefly
            type_map = {
                "t": "task",
                "n": "note",
                "e": "event",
                "*": "priority",
                "x": "done",
            }
            lines = ["", f"[dim italic]parsed {len(entries)} entries:[/dim italic]", ""]
            for sym, entry_text in entries:
                d = SYMBOL_DISPLAY.get(sym, sym)
                label = type_map.get(sym, sym)
                lines.append(f"  {d} {entry_text}  [dim italic]{label}[/dim italic]")
            inline_text = "\n".join(lines)

            def show_result():
                self._exit_dump_mode()
                inline = self.query_one("#inline-display", Static)
                inline.update(inline_text)
                inline.display = True
                self.refresh_log()

            self.app.call_from_thread(show_result)
        elif err == "no_key":

            def show_key_error():
                self._exit_dump_mode()
                show_setup_instructions()

            self.app.call_from_thread(show_key_error)
        else:

            def show_other_error():
                self._exit_dump_mode()
                inline = self.query_one("#inline-display", Static)
                inline.update(
                    f"[red]Error: {err}[/red]\n[dim italic]Draft saved in log. Try: bujo dump --retry[/dim italic]"
                )
                inline.display = True

            self.app.call_from_thread(show_other_error)

    def on_key(self, event: events.Key) -> None:
        # Coach dismiss: any key (except ctrl+b) closes coach
        if self._current_coach_mode:
            if event.key != "ctrl+b":
                self._close_coach()
                event.stop()
            return

        # Dump mode: Ctrl+Enter (ctrl+j) to submit, Escape to cancel
        if self.dump_mode:
            if event.key == "escape":
                self._exit_dump_mode()
                event.stop()
                return
            if event.key == "ctrl+j":
                self._submit_dump()
                event.stop()
                return
            return

        key = event.key

        # Escape toggles mode regardless of current mode
        if key == "escape":
            self._input_text = ""
            if self.nav_mode:
                self.nav_mode = False
                self._update_input_display()
            else:
                entries = parse_entries(today_log(), today_path(), date.today())
                if entries:
                    self.nav_mode = True
                    self._set_nav_focus_last()
                else:
                    self._update_input_display()
            event.stop()
            return

        # Enter submits input in input mode
        if key == "enter" and not self.nav_mode:
            self._submit_input()
            event.stop()
            return

        # Backspace deletes last char in input mode
        if key == "backspace" and not self.nav_mode:
            if self._input_text:
                self._input_text = self._input_text[:-1]
                self._update_input_display()
            event.stop()
            return

        # Handle nav mode actions
        if self.nav_mode:
            if key == "up":
                lv = self.query_one("#entry-list", ListView)
                if lv.children and lv.index is not None and lv.index > 0:
                    lv.index -= 1
                event.stop()
                return
            elif key == "down":
                lv = self.query_one("#entry-list", ListView)
                if (
                    lv.children
                    and lv.index is not None
                    and lv.index < len(lv.children) - 1
                ):
                    lv.index += 1
                event.stop()
                return
            elif key == "x":
                entry = self._get_selected_entry()
                if entry:
                    self._rewrite_entry(entry["raw"], "x", entry["text"])
                    self.refresh_log()
                event.stop()
                return
            elif key == "k":
                entry = self._get_selected_entry()
                if entry:
                    self._rewrite_entry(entry["raw"], "k", entry["text"])
                    self.refresh_log()
                event.stop()
                return
            elif key == ">":
                entry = self._get_selected_entry()
                if entry:
                    self._rewrite_entry(entry["raw"], ">", entry["text"])
                    self.refresh_log()
                event.stop()
                return
            elif key == "r":
                entry = self._get_selected_entry()
                if entry:
                    self._rewrite_entry(entry["raw"], ">", entry["text"])
                    self._input_text = entry["text"]
                    self.nav_mode = False
                    self._update_input_display()
                event.stop()
                return
            elif key == "m":
                self.app.push_screen(MonthlyView())
                event.stop()
                return
            elif key == "f":
                self.app.push_screen(FutureView())
                event.stop()
                return
            elif key == "shift+m":
                self.app.push_screen(MigrationScreen())
                event.stop()
                return
            elif key == "question_mark":
                self.app.push_screen(HelpScreen())
                event.stop()
                return
            elif key == "q":
                self.app.exit()
                event.stop()
                return
            elif key in ("t", "n", "e", "star", "p"):
                # Prefix key typed in nav mode — switch to input, add key to buffer
                self.nav_mode = False
                prefix_map = {"t": "t ", "n": "n ", "e": "e ", "star": "* ", "p": "p "}
                self._input_text = prefix_map.get(key, "")
                self._update_input_display()
                event.stop()
                return
            return

        # Input mode: handle printable characters
        # Accept any key that has a printable character
        char = event.character
        if char and char.isprintable() and char not in ("\n", "\r", "\t"):
            self._input_text += char
            self._update_input_display()
            event.stop()
            return

        # Also handle keys without character attribute (like "space")
        if key == "space":
            self._input_text += " "
            self._update_input_display()
            event.stop()
            return


# ── App ────────────────────────────────────────────────


class BuJoApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "BuJo"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        ensure_vault()
        self.push_screen(DailyView())


def main() -> None:
    ensure_vault()
    app = BuJoApp()
    # Run with explicit terminal settings for better Windows compatibility
    app.run(headless=False, size=(80, 24))


if __name__ == "__main__":
    main()
