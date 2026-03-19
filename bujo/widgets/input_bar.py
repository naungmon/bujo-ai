"""BuJo input bar — TextArea subclass with focus transfer on arrow-up.

When the cursor is on the first line (or the TextArea is empty),
arrow-up transfers focus to the entry list instead of moving the
cursor within the TextArea.
"""

from textual.widgets import TextArea
from textual import events


class BuJoInput(TextArea):
    """Main input TextArea that transfers focus on arrow-up at first line."""

    def _on_key(self, event: events.Key) -> None:
        if event.key == "up":
            # Transfer focus if on first line or empty
            cursor_row = self.cursor_location[0]
            if cursor_row == 0 or not self.text.strip():
                try:
                    entry_list = self.screen.query_one("#entry-list")
                    if entry_list.children:
                        entry_list.focus()
                        event.prevent_default()
                        event.stop()
                        return
                except Exception:
                    pass
        super()._on_key(event)
