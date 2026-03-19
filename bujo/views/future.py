"""Future log view."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Input, Static
from textual import on

from bujo.vault import get_future_path, read_text_safe, append_entry, open_in_editor


class FutureView(Screen):
    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding("a", "add_item", "Add"),
        Binding("e", "edit_raw", "Edit"),
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
                "[dim italic]a add \u00b7 e edit in $EDITOR \u00b7 Escape back[/dim italic]",
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
        self.query_one("#secondary-content", Static).update(content)

    @on(Input.Submitted, "#add-input")
    def on_add_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if text:
            append_entry(">", text)
        self.query_one("#add-container").remove()
        self._load_content()

    def action_add_item(self) -> None:
        self.query_one("#secondary-layout").mount(
            Static("[dim]New future item:[/dim]", id="add-label"),
            Input(placeholder="park for later...", id="add-input"),
            after=self.query_one("#secondary-hints"),
        )
        self.query_one("#add-input", Input).focus()

    def action_edit_raw(self) -> None:
        open_in_editor(get_future_path())
        self._load_content()
