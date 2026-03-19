"""Tutorial screen — step-by-step walkthrough for new users."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Center
from textual.screen import Screen
from textual.widgets import Static
from textual import events


class TutorialScreen(Screen):
    """Step-by-step tutorial overlay. Any key advances, Escape skips."""

    STEPS = [
        (
            "[bold]Welcome to BuJo[/bold]\n\n"
            "[dim]your ADHD-friendly bullet journal[/dim]\n\n"
            "BuJo stores everything as plain markdown files.\n"
            "Your vault works in Obsidian too."
        ),
        (
            "[bold]Prefix sets the type[/bold]\n\n"
            "[dim]start any line with a prefix:[/dim]\n\n"
            "[cyan]t[/cyan] or [cyan]task[/cyan]       → task\n"
            "[magenta]e[/magenta] or [cyan]event[/cyan]      → event\n"
            "[white]n[/white] or [white]note[/white]       → note\n"
            "[red]*[/red] or [red]priority[/red]   → priority\n"
            "[green]x[/green] or [green]done[/green]       → done\n"
            "[dim]k[/dim] or [dim]kill[/dim]        → killed\n"
            "[blue]>[/blue]                   → migrated\n\n"
            "[dim italic](no prefix = note)[/dim italic]"
        ),
        (
            "[bold]Priority shortcut[/bold]\n\n"
            "[dim]add ! at the end of any line → becomes priority[/dim]\n\n"
            "  finish this report!    →  ★ finish this report\n"
            "  call jackson!          →  ★ call jackson\n\n"
            "[dim italic]works with any prefix[/dim italic]"
        ),
        (
            "[bold]Arrow keys[/bold] — navigate between input and entries\n\n"
            "↑ from the top of your entry list → focuses the input bar\n"
            "↓ from the input bar → focuses your entry list\n\n"
            "[dim]one key to move, no mode switching needed[/dim]"
        ),
        (
            "[bold]Update entries[/bold]\n\n"
            "[dim]select an entry, then:[/dim]\n\n"
            "  [green]x[/green]  → mark done\n"
            "  [dim]k[/dim]  → kill (consciously drop it)\n"
            "  [blue]>[/blue] → migrate (carry it forward)\n"
            "  Enter → edit the text\n"
            "  Ctrl+Z → undo last change"
        ),
        (
            "[bold]AI-powered input[/bold]\n\n"
            "[dim]type freely, AI sorts it into entries[/dim]\n\n"
            "Just type. No prefix needed. AI figures out tasks vs notes.\n"
            "Hit [bold]Enter[/bold] and BuJo parses your thought.\n\n"
            "[dim]Use prefixes like t task, n note, * priority for explicit types[/dim]"
        ),
        (
            "[bold]Three views[/bold]\n\n"
            "  [cyan]m[/cyan]  → monthly priorities (3-5 things this month)\n"
            "  [cyan]f[/cyan]  → future log (parked, not dead)\n"
            "  [cyan]Shift+M[/cyan]  → migration pass (review all pending tasks)\n"
            "  [cyan]Shift+R[/cyan]  → monthly review\n\n"
            "[dim italic]each serves a specific purpose in the system[/dim italic]"
        ),
        (
            "[bold]Coach — Ctrl+B[/bold]\n\n"
            "[dim]insights built for ADHD brains[/dim]\n\n"
            "After a few days of logging, Coach shows:\n"
            "  · what keeps getting avoided\n"
            "  · your momentum and streak\n"
            "  · what's actually working\n\n"
            "[dim]best used when you feel stuck or scattered[/dim]"
        ),
    ]

    def compose(self) -> ComposeResult:
        self._step_index = 0
        with Center():
            with Vertical(id="tut-container"):
                yield Static("", id="tut-text")
                yield Static("", id="tut-footer")

    def on_mount(self) -> None:
        self._show_step(0)

    def _show_step(self, index: int) -> None:
        if index >= len(self.STEPS):
            self.app.pop_screen()
            return
        self._step_index = index
        text = self.query_one("#tut-text", Static)
        footer = self.query_one("#tut-footer", Static)
        text.update(self.STEPS[index])
        footer.update(
            f"[dim]{index + 1}/{len(self.STEPS)}[/dim]  "
            "[dim]any key next · Escape to skip[/dim]"
        )

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.app.pop_screen()
            return
        self._show_step(self._step_index + 1)
