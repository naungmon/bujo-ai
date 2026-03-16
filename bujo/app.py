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
from textual.widgets import Footer, Header, Input, ListView, ListItem, Static
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

    BINDINGS = [
        Binding("escape", "toggle_mode", "Toggle mode"),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("x", "mark_done", "Done", show=False),
        Binding("k", "kill_entry", "Kill", show=False),
        Binding(">", "migrate_entry", "Migrate", show=False),
        Binding("r", "retype_entry", "Retype", show=False),
        Binding("m", "monthly", "Monthly"),
        Binding("f", "future", "Future"),
        Binding("M", "migration", "Migrate all"),
        Binding("?", "help", "Help"),
        Binding("q", "quit", "Quit"),
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
            yield Static("\u25b8 ", id="input-prompt")
            yield Input(placeholder="", id="main-input")
        yield Footer()

    def on_mount(self) -> None:
        self._current_coach_mode = False
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
            self._set_input_focus()
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
            self._set_nav_focus_last()

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
        inp = self.query_one("#main-input", Input)
        inp.focus()

    def _set_nav_focus_last(self) -> None:
        lv = self.query_one("#entry-list", ListView)
        if lv.children:
            lv.focus()
            # Move to last entry
            lv.index = len(lv.children) - 1

    def _update_hint_bar(self) -> None:
        hint = self.query_one("#hint-bar", Static)
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

    def action_toggle_mode(self) -> None:
        if self._current_coach_mode:
            self._close_coach()
            return

        if self.nav_mode:
            self.nav_mode = False
            self._set_input_focus()
        else:
            self.nav_mode = True
            self._set_nav_focus_last()

    def action_cursor_up(self) -> None:
        if not self.nav_mode:
            return
        lv = self.query_one("#entry-list", ListView)
        if lv.children and lv.index is not None and lv.index > 0:
            lv.index -= 1

    def action_cursor_down(self) -> None:
        if not self.nav_mode:
            return
        lv = self.query_one("#entry-list", ListView)
        if lv.children and lv.index is not None and lv.index < len(lv.children) - 1:
            lv.index += 1

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
        inp = self.query_one("#main-input", Input)
        inp.value = entry["text"]
        # Switch to input mode
        self.nav_mode = False
        inp.focus()

    def action_monthly(self) -> None:
        self.app.push_screen(MonthlyView())

    def action_future(self) -> None:
        self.app.push_screen(FutureView())

    def action_migration(self) -> None:
        self.app.push_screen(MigrationScreen())

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())

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

        # Dismiss on any key
        self.query_one("#main-input", Input).focus()

    def _close_coach(self) -> None:
        self._current_coach_mode = False
        inline = self.query_one("#inline-display", Static)
        inline.update("")
        inline.display = False
        self.refresh_log()

    @on(Input.Submitted, "#main-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._current_coach_mode:
            self._close_coach()
            event.input.clear()
            return

        text = event.value.strip()
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

        event.input.clear()
        self.refresh_log()

    def on_key(self, event: events.Key) -> None:
        if self._current_coach_mode and event.key not in ("escape", "q"):
            self._close_coach()
            event.stop()
            return

        if self.nav_mode and event.key in ("t", "n", "e", "*", "p"):
            # Valid prefix typed → switch to input mode, let Input handle it
            self.nav_mode = False
            self._set_input_focus()


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
    app.run()


if __name__ == "__main__":
    main()
