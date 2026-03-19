"""Tests for bujo.hints — progressive disclosure system."""

import json
from pathlib import Path

import pytest

from bujo.hints import HintManager


class TestHintManager:
    def test_first_entry_hint(self, tmp_path):
        mgr = HintManager(state_path=tmp_path / "hints.json")
        hint = mgr.check("first_entry")
        assert hint is not None
        assert "tip:" in hint

    def test_hint_shown_once(self, tmp_path):
        mgr = HintManager(state_path=tmp_path / "hints.json")
        first = mgr.check("first_entry")
        assert first is not None
        second = mgr.check("first_entry")
        assert second is None

    def test_state_persists(self, tmp_path):
        state_file = tmp_path / "hints.json"
        mgr1 = HintManager(state_path=state_file)
        mgr1.check("first_entry")
        # New instance reads persisted state
        mgr2 = HintManager(state_path=state_file)
        assert mgr2.check("first_entry") is None

    def test_unknown_milestone_returns_none(self, tmp_path):
        mgr = HintManager(state_path=tmp_path / "hints.json")
        assert mgr.check("nonexistent_milestone") is None

    def test_all_milestones_defined(self, tmp_path):
        mgr = HintManager(state_path=tmp_path / "hints.json")
        expected = {"first_entry", "three_entries", "first_nav", "five_entries_session", "multi_day"}
        assert set(mgr.HINTS.keys()) == expected

    def test_entry_count_check(self, tmp_path):
        mgr = HintManager(state_path=tmp_path / "hints.json")
        assert mgr.check_entry_count(0) is None
        hint = mgr.check_entry_count(1)
        assert hint is not None  # first_entry hint
        assert mgr.check_entry_count(1) is None  # already shown
        hint3 = mgr.check_entry_count(3)
        assert hint3 is not None  # three_entries hint
        hint5 = mgr.check_entry_count(5)
        assert hint5 is not None  # five_entries_session hint
