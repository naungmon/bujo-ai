"""Session-scoped undo stack for BuJo.

Each action (add, edit, status_change) is recorded with enough
information to reverse it by modifying the markdown file directly.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class UndoAction:
    action_type: str        # "add", "edit", "status_change"
    file_path: Path         # which markdown file was modified
    original_line: str      # line content before action ("" for add)
    new_line: str           # line content after action
    description: str        # human-readable, e.g. 'mark done "call Jackson"'


class UndoStack:
    """Session-scoped undo stack. Clears on app close."""

    def __init__(self) -> None:
        self._stack: list[UndoAction] = []

    def push(self, action: UndoAction) -> None:
        self._stack.append(action)

    def pop(self) -> UndoAction | None:
        return self._stack.pop() if self._stack else None

    @property
    def is_empty(self) -> bool:
        return len(self._stack) == 0

    def undo(self) -> UndoAction | None:
        """Pop the last action and reverse it in the file.

        Returns the undone action, or None if stack is empty.
        """
        action = self.pop()
        if action is None:
            return None

        try:
            content = action.file_path.read_text(encoding="utf-8")
        except (OSError, PermissionError):
            return action  # can't read file, but still return the action

        if action.action_type == "add":
            idx = content.rfind(action.new_line + "\n")
            if idx != -1:
                content = content[:idx] + content[idx + len(action.new_line) + 1:]
            else:
                idx = content.rfind(action.new_line)
                if idx != -1:
                    content = content[:idx] + content[idx + len(action.new_line):]
        elif action.action_type in ("edit", "status_change"):
            idx = content.rfind(action.new_line)
            if idx != -1:
                content = content[:idx] + action.original_line + content[idx + len(action.new_line):]
            else:
                content = content.replace(action.new_line, action.original_line, 1)

        action.file_path.write_text(content, encoding="utf-8")
        return action
