"""Progressive disclosure hints for BuJo.

Shows milestone-triggered hints exactly once. State persists
in ~/.bujo-hints-seen (JSON file).
"""

import json
from pathlib import Path


class HintManager:
    """Tracks which hints have been shown and triggers new ones at milestones."""

    HINTS = {
        "first_entry": 'tip: start with "t" for task, "e" for event, or just type naturally',
        "three_entries": "tip: use arrow keys to browse your entries",
        "first_nav": "tip: press x to mark done, k to kill, Enter to edit",
        "five_entries_session": "tip: Ctrl+B for coaching insights",
        "multi_day": "tip: press / to search across all your days",
    }

    def __init__(self, state_path: Path | None = None) -> None:
        self._state_path = state_path or (Path.home() / ".bujo-hints-seen")
        self._seen: set[str] = set()
        self._load()

    def _load(self) -> None:
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                self._seen = set(data.get("seen", []))
            except (json.JSONDecodeError, OSError):
                self._seen = set()

    def _save(self) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(
                json.dumps({"seen": list(self._seen)}),
                encoding="utf-8",
            )
        except OSError:
            pass

    def check(self, milestone: str) -> str | None:
        """Check if a hint should be shown for this milestone.

        Returns the hint text if it hasn't been shown yet, None otherwise.
        Marks the hint as seen.
        """
        if milestone not in self.HINTS:
            return None
        if milestone in self._seen:
            return None
        self._seen.add(milestone)
        self._save()
        return self.HINTS[milestone]

    def check_entry_count(self, count: int) -> str | None:
        """Check entry-count-based milestones. Call after each new entry."""
        if count >= 1:
            hint = self.check("first_entry")
            if hint:
                return hint
        if count >= 3:
            hint = self.check("three_entries")
            if hint:
                return hint
        if count >= 5:
            hint = self.check("five_entries_session")
            if hint:
                return hint
        return None
