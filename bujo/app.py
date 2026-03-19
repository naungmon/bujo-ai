"""BuJo Textual TUI application — slim shell.

DailyView and widgets live in bujo.views and bujo.widgets.
This module provides BuJoApp, main(), and re-exports for
backward compatibility with cli.py and other consumers.
"""

from textual.app import App
from textual.binding import Binding

# ── Re-exports (used by cli.py, ai.py, capture_hotkey.py, etc.) ──
from bujo.symbols import SYMBOLS, SYMBOL_DISPLAY, SYMBOL_COLORS, ENTRY_SORT_ORDER  # noqa: F401
from bujo.vault import (  # noqa: F401
    VAULT, DAILY, FUTURE, MONTHLY, REFLECTIONS, FIRST_RUN_FLAG,
    open_in_editor, ensure_vault, today_path, read_text_safe,
    today_log, save_today, append_entry, get_monthly_path,
    get_future_path, has_any_daily_files, get_all_logs_summary,
)

# ── Views ─────────────────────────────────────────────
from bujo.views.daily import DailyView  # noqa: F401
from bujo.widgets.entry_list import EntryItem, format_entry  # noqa: F401


# ── App ────────────────────────────────────────────────


class BuJoApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "BuJo"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        ensure_vault()
        self.push_screen(DailyView())


def main() -> None:
    ensure_vault()
    app = BuJoApp()
    app.run(headless=False, size=(80, 24))


if __name__ == "__main__":
    main()
