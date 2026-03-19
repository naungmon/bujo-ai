"""Tests for bujo.undo — session-scoped undo stack."""

from pathlib import Path

import pytest

from bujo.undo import UndoAction, UndoStack


class TestUndoAction:
    def test_fields(self):
        a = UndoAction(
            action_type="add",
            file_path=Path("daily/2026-03-17.md"),
            original_line="",
            new_line="t buy milk",
            description='add "buy milk"',
        )
        assert a.action_type == "add"
        assert a.new_line == "t buy milk"


class TestUndoStack:
    def test_empty_pop_returns_none(self):
        stack = UndoStack()
        assert stack.pop() is None

    def test_push_and_pop(self):
        stack = UndoStack()
        a = UndoAction("add", Path("f.md"), "", "t test", "add")
        stack.push(a)
        assert stack.pop() == a

    def test_lifo_order(self):
        stack = UndoStack()
        a1 = UndoAction("add", Path("f.md"), "", "t first", "add first")
        a2 = UndoAction("add", Path("f.md"), "", "t second", "add second")
        stack.push(a1)
        stack.push(a2)
        assert stack.pop() == a2
        assert stack.pop() == a1

    def test_is_empty(self):
        stack = UndoStack()
        assert stack.is_empty
        stack.push(UndoAction("add", Path("f.md"), "", "t x", "add"))
        assert not stack.is_empty

    def test_apply_undo_add(self, tmp_path):
        """Undo an 'add' removes the new_line from the file."""
        f = tmp_path / "test.md"
        f.write_text("# Header\n\nt buy milk\n", encoding="utf-8")
        stack = UndoStack()
        action = UndoAction("add", f, "", "t buy milk", 'add "buy milk"')
        stack.push(action)
        result = stack.undo()
        assert result is not None
        content = f.read_text(encoding="utf-8")
        assert "t buy milk" not in content
        assert "# Header" in content

    def test_apply_undo_status_change(self, tmp_path):
        """Undo a status change restores original_line."""
        f = tmp_path / "test.md"
        f.write_text("# Header\n\nx buy milk\n", encoding="utf-8")
        stack = UndoStack()
        action = UndoAction("status_change", f, "t buy milk", "x buy milk", "mark done")
        stack.push(action)
        result = stack.undo()
        assert result is not None
        content = f.read_text(encoding="utf-8")
        assert "t buy milk" in content
        assert "x buy milk" not in content

    def test_apply_undo_edit(self, tmp_path):
        """Undo an edit restores original text."""
        f = tmp_path / "test.md"
        f.write_text("# Header\n\nt buy oat milk\n", encoding="utf-8")
        stack = UndoStack()
        action = UndoAction("edit", f, "t buy milk", "t buy oat milk", "edit")
        stack.push(action)
        result = stack.undo()
        assert result is not None
        content = f.read_text(encoding="utf-8")
        assert "t buy milk" in content
        assert "t buy oat milk" not in content

    def test_undo_empty_returns_none(self):
        stack = UndoStack()
        assert stack.undo() is None
