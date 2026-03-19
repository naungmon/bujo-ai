"""Monthly review screen — multi-perspective AI synthesis."""

import asyncio
import calendar
from datetime import date, timedelta

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Static, ListView, ListItem
from textual import on, work

from bujo.models import LogReader
from bujo.vault import VAULT, DAILY, read_text_safe, get_future_items_for_month, append_entry, mark_future_entry_done
from bujo.symbols import SYMBOL_DISPLAY


class ReviewView(Screen):
    """Run a monthly review with AI perspective synthesis."""

    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
    ]

    def __init__(self, year: int = 0, month: int = 0) -> None:
        super().__init__()
        today = date.today()
        self._year = year if year else today.year
        self._month = month if month else today.month
        self._future_items: list[str] = []
        self._pulled_items: list[str] = []

    def compose(self) -> ComposeResult:
        month_name = date(self._year, self._month, 1).strftime("%B %Y")
        with Vertical(id="secondary-layout"):
            yield Static(f"[bold]Monthly Review — {month_name}[/bold]", id="secondary-title")
            yield Static("\u2500" * 40, id="secondary-separator")
            yield ScrollableContainer(
                Static("", id="review-content"),
                id="secondary-scroll",
            )
            yield Static("", id="future-section")
            yield Static(
                "[dim italic]Escape to close[/dim italic]",
                id="secondary-hints",
            )

    def on_mount(self) -> None:
        self._run_review()

    @work(thread=False)
    async def _run_review(self) -> None:
        content = self.query_one("#review-content", Static)
        content.update("[dim italic]loading entries...[/dim italic]")

        self._load_future_log_section()

        journal_content = self._load_month_entries()
        if not journal_content.strip():
            content.update("[dim italic]no entries found for this month.[/dim italic]")
            return

        entry_count = journal_content.count("\n")
        content.update(
            f"[dim italic]found ~{entry_count} lines. running perspectives...[/dim italic]"
        )

        completed: list[str] = []

        def on_perspective_complete(name: str) -> None:
            completed.append(name)
            self.app.call_from_thread(
                content.update,
                f"[dim italic]perspectives: {', '.join(completed)} done "
                f"({len(completed)}/6)[/dim italic]",
            )

        def on_synthesis_start() -> None:
            self.app.call_from_thread(
                content.update,
                "[dim italic]all perspectives done. synthesizing...[/dim italic]",
            )

        try:
            from bujo.review import run_monthly_review

            report = await run_monthly_review(
                journal_content,
                on_perspective_complete,
                on_synthesis_start,
                year=self._year,
                month=self._month,
            )
            content.update(report)
        except RuntimeError as e:
            if "no_key" in str(e):
                content.update(
                    "[red]No API key set.[/red]\n\n"
                    "[dim]Set BUJO_AI_KEY in your environment.\n"
                    "Get a key at openrouter.ai/keys[/dim]"
                )
            elif "rate_limited" in str(e):
                content.update(
                    "[yellow]Rate limited.[/yellow] Wait a minute and try again."
                )
            else:
                content.update(f"[red]Error: {e}[/red]")
        except Exception as e:
            content.update(f"[red]Review failed: {e}[/red]")

    def _load_future_log_section(self) -> None:
        """Show future log items for the review month."""
        section = self.query_one("#future-section", Static)
        self._future_items = get_future_items_for_month(self._year, self._month)

        if not self._future_items:
            section.update("")
            return

        display = SYMBOL_DISPLAY.get("<", "<")
        items_markup = "\n".join(
            f"  [blue]{display}[/blue] {item}" for item in self._future_items
        )
        section.update(
            f"[bold cyan]From your future log[/bold cyan]\n"
            f"{items_markup}\n"
            f"[dim italic]pull: select item to schedule | done: mark completed[/dim italic]"
        )

    def _load_month_entries(self) -> str:
        """Load all daily entries for self._year / self._month."""
        first_day = date(self._year, self._month, 1)
        _, last_day_num = calendar.monthrange(self._year, self._month)
        last_day = date(self._year, self._month, last_day_num)

        lines: list[str] = []
        d = first_day
        while d <= last_day:
            path = DAILY / f"{d.isoformat()}.md"
            if path.exists():
                content = read_text_safe(path)
                if content.strip():
                    lines.append(f"## {d.isoformat()}\n")
                    lines.append(content.strip())
                    lines.append("")
            d += timedelta(days=1)

        return "\n".join(lines)
