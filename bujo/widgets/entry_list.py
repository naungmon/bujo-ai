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


def format_entry(entry, source_date=None) -> str:
    """Format an Entry object or dict as markup for ListView.

    If source_date is provided (date object), prepends a date label
    indicating where the task originated (for migration items).
    """
    if hasattr(entry, "symbol"):
        sym, display, text, etype = entry.symbol, entry.display, entry.text, entry.type
    else:
        sym = entry.get("symbol", "")
        display = entry.get("display", "")
        text = entry.get("text", "")
        etype = entry.get("type", "")

    color = SYMBOL_COLORS.get(sym, "white")
    date_label = ""
    if source_date is not None:
        date_label = f"[dim]{source_date.strftime('%b %d')}: [/dim]"
    if sym == "x":
        return f"{date_label}[{color} dim]{display}[/] [dim]{text}[/]  [dim italic]{etype}[/]"
    elif sym == "k":
        return f"{date_label}[dim]{display}[/] [dim]{text}[/]  [dim italic]{etype}[/]"
    elif sym == "*":
        return f"{date_label}[{color} bold]{display}[/] [bold]{text}[/]  [dim italic]{etype}[/]"
    else:
        return f"{date_label}[{color}]{display}[/] [white]{text}[/]  [dim italic]{etype}[/]"


class EntryItem(ListItem):
    """A list item representing a BuJo entry, with inline edit support."""

    def __init__(self, entry, index: int) -> None:
        super().__init__()
        self.entry = entry
        self.entry_index = index
        self._editing = False

    def compose(self) -> ComposeResult:
        src = self.entry.get("source_date") if isinstance(self.entry, dict) else None
        yield Static(format_entry(self.entry, src), id="entry-display")

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
