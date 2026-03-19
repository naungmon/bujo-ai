"""Migration screen — review and triage pending tasks."""

from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import ListView, ListItem, Static

from bujo.models import parse_entries
from bujo.vault import DAILY, read_text_safe, get_future_path, append_entry


class MigrationScreen(Screen):
    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding(">", "keep", "Keep"),
        Binding("d", "kill", "Kill"),
        Binding("p", "to_future", "Future"),
        Binding("t", "keep", "Keep"),
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="secondary-layout"):
            yield Static("[bold]Migration[/bold]", id="secondary-title")
            yield Static("\u2500" * 40, id="secondary-separator")
            yield Static("", id="mig-status")
            yield ListView(id="mig-list")
            yield Static(
                "[dim italic]> keep \u00b7 d kill \u00b7 p future \u00b7 t keep \u00b7 "
                "\u2191\u2193 navigate \u00b7 Escape done[/dim italic]",
                id="secondary-hints",
            )

    def on_mount(self) -> None:
        self.pending: list[dict] = []
        self._scrolled = False
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

        self.query_one("#mig-status", Static).update(
            "[dim italic]scroll to review...[/dim italic]"
        )
        from bujo.widgets.entry_list import EntryItem
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
        elif self._scrolled:
            count = len(self.pending)
            self.query_one("#mig-status", Static).update(
                f"[dim italic]{count} pending \u2014 "
                f"would you write this again today?[/dim italic]"
            )

    def action_keep(self) -> None:
        lv = self.query_one("#mig-list", ListView)
        if lv.highlighted_child is None or lv.index is None:
            return
        if lv.index >= len(self.pending):
            return
        entry = self.pending[lv.index]
        append_entry(entry["symbol"], entry["text"])
        self._replace_in_source(entry, ">")
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
        lv = self.query_one("#mig-list", ListView)
        lv.action_cursor_down()
        if not self._scrolled and self.pending:
            self._scrolled = True
            count = len(self.pending)
            self.query_one("#mig-status", Static).update(
                f"[dim italic]{count} pending \u2014 "
                f"would you write this again today?[/dim italic]"
            )

    def action_cursor_up(self) -> None:
        lv = self.query_one("#mig-list", ListView)
        lv.action_cursor_up()
        if not self._scrolled and self.pending:
            self._scrolled = True
            count = len(self.pending)
            self.query_one("#mig-status", Static).update(
                f"[dim italic]{count} pending \u2014 "
                f"would you write this again today?[/dim italic]"
            )
