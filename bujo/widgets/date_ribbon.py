"""Date ribbon widget — horizontal day navigator.

Shows: <- Mar 16       Monday, March 17 2026       Mar 18 ->
Supports [ and ] keys for navigation.
"""

from datetime import date, timedelta

from textual.widgets import Static
from textual.reactive import reactive


class DateRibbon(Static):
    """Displays current viewing date with prev/next indicators."""

    viewing_date: reactive[date] = reactive(date.today)

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)

    def watch_viewing_date(self, value: date) -> None:
        self._render_ribbon()

    def on_mount(self) -> None:
        self._render_ribbon()

    def _render_ribbon(self) -> None:
        d = self.viewing_date
        today = date.today()
        prev_day = d - timedelta(days=1)
        next_day = d + timedelta(days=1)

        prev_label = prev_day.strftime("%b %d")
        next_label = next_day.strftime("%b %d")
        center = d.strftime("%A, %B %d %Y")

        if d == today:
            center_fmt = f"[bold]{center}[/bold]"
        else:
            center_fmt = f"[dim]{center}[/dim]"

        self.update(
            f"  [dim]<[/dim] {prev_label}       {center_fmt}       {next_label} [dim]>[/dim]"
        )

    def go_prev(self) -> None:
        self.viewing_date = self.viewing_date - timedelta(days=1)

    def go_next(self) -> None:
        """Navigate to next day. Future days are allowed (spec says they show as empty)."""
        self.viewing_date = self.viewing_date + timedelta(days=1)

    @property
    def is_viewing_today(self) -> bool:
        return self.viewing_date == date.today()
