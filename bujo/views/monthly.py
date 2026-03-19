"""Monthly priorities view."""

from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Input, Static
from textual import on

from bujo.vault import get_monthly_path, read_text_safe, append_entry, open_in_editor


class MonthlyView(Screen):
    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding("a", "add_priority", "Add"),
        Binding("e", "edit_raw", "Edit"),
    ]

    def compose(self) -> ComposeResult:
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
        self._load_content()

    def _load_content(self) -> None:
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
        self.query_one("#add-container").remove()
        self._load_content()

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
        self._load_content()
