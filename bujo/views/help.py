"""Help screen — updated for the modeless interaction model."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Static


class HelpScreen(Screen):
    BINDINGS = [Binding("escape,q", "app.pop_screen", "Close")]

    def compose(self) -> ComposeResult:
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
                    "[dim italic]interaction[/dim italic]\n"
                    "  \u2191 \u2193    move between input and entries\n"
                    "  Enter  submit (input) or edit (entry)\n"
                    "  Escape cancel edit\n"
                    "  x      mark done\n"
                    "  k      kill\n"
                    "  >      migrate\n"
                    "  Ctrl+Z undo last action\n\n"
                    "[dim italic]navigation[/dim italic]\n"
                    "  [  ]       previous / next day\n"
                    "  /          search across days\n\n"
                    "[dim italic]views[/dim italic]\n"
                    "  m          monthly log\n"
                    "  f          future log\n"
                    "  Shift+M    migration pass\n"
                    "  Shift+R    monthly review\n"
                    "  Ctrl+B  coach\n"
                    "  ?          this screen\n"
                    "  q          quit\n\n"
                    "[dim italic]run [cyan]bujo tutorial[/cyan] for a step-by-step walkthrough[/dim italic]\n",
                    markup=True,
                ),
            )
            yield Static(
                "[dim italic]Escape to close[/dim italic]",
                id="secondary-hints",
            )
