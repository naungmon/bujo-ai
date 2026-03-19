"""Future log view — month-grouped parking for future tasks."""

import calendar
import re
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Input, Static
from textual import on

from bujo.vault import get_future_path, read_text_safe, append_future_entry
from bujo.symbols import SYMBOL_DISPLAY


class FutureView(Screen):
    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding("a", "add_item", "Add"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="secondary-layout"):
            yield Static("[bold]Future Log[/bold]", id="secondary-title")
            yield Static("\u2500" * 40, id="secondary-separator")
            yield ScrollableContainer(
                Static("", id="secondary-content"),
                id="secondary-scroll",
            )
            yield Static(
                "[dim italic]a add \u00b7 Escape back[/dim italic]",
                id="secondary-hints",
            )

    def on_mount(self) -> None:
        self._load_content()

    def _load_content(self) -> None:
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
        formatted = self._format_for_display(content)
        self.query_one("#secondary-content", Static).update(formatted)

    def _format_for_display(self, content: str) -> str:
        """Render future.md content as marked-up text for display."""
        if not content.strip():
            return "[dim]empty. Press a to park something.[/dim]"

        lines: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("## "):
                lines.append(f"\n[bold cyan]{stripped[3:]}[/bold cyan]")
            elif stripped.startswith("> "):
                text = stripped[2:]
                lines.append(f"  [blue]{SYMBOL_DISPLAY['>']}[/blue] {text}")
            else:
                lines.append(f"[dim]{stripped}[/dim]")

        return "\n".join(lines) if lines else "[dim]empty. Press a to park something.[/dim]"

    def _detect_month(self, text: str) -> str | None:
        """Detect a month name in text and return 'Month YYYY' label.

        Examples:
            "call dentist june" -> "June 2026"
            "august trip to thailand" -> "August 2026"
            "September: renew visa" -> "September 2026"
            "june 2027" -> "June 2027"
            "just a task" -> None
        """
        lower = text.lower()
        now = date.today()

        month_pattern = r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b"
        m = re.search(month_pattern, lower)
        if not m:
            return None

        month_name = m.group(1).capitalize()
        month_num = list(calendar.month_name).index(month_name)

        year_m = re.search(r"\b(20\d{2})\b", text)
        year = int(year_m.group(1)) if year_m else now.year

        if year < now.year or (year == now.year and month_num < now.month):
            year += 1

        return f"{month_name} {year}"

    @on(Input.Submitted, "#add-input")
    def on_add_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        month_label = self._detect_month(text)
        append_future_entry(text, month_label)

        self.query_one("#add-container").remove()
        self._load_content()

    def action_add_item(self) -> None:
        from textual.containers import Container

        self.query_one("#secondary-layout").mount(
            Static("[dim]New future item:[/dim]", id="add-label"),
            Input(placeholder="park for later... (optional: add month, e.g. june)", id="add-input"),
            after=self.query_one("#secondary-hints"),
        )
        self.query_one("#add-input", Input).focus()
