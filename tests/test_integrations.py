"""Tests for bujo.integrations — Obsidian frontmatter and dashboard."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bujo.integrations import (
    should_add_frontmatter,
    should_generate_dashboard,
    add_frontmatter,
    generate_dashboard,
)


# ---------------------------------------------------------------------------
# Environment flag checks
# ---------------------------------------------------------------------------


class TestEnvFlags:
    def test_frontmatter_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("BUJO_OBSIDIAN_FRONTMATTER", raising=False)
        assert should_add_frontmatter() is False

    def test_frontmatter_enabled(self, monkeypatch):
        monkeypatch.setenv("BUJO_OBSIDIAN_FRONTMATTER", "1")
        assert should_add_frontmatter() is True

    def test_frontmatter_wrong_value(self, monkeypatch):
        monkeypatch.setenv("BUJO_OBSIDIAN_FRONTMATTER", "yes")
        assert should_add_frontmatter() is False

    def test_dashboard_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("BUJO_DASHBOARD", raising=False)
        assert should_generate_dashboard() is False

    def test_dashboard_enabled(self, monkeypatch):
        monkeypatch.setenv("BUJO_DASHBOARD", "1")
        assert should_generate_dashboard() is True


# ---------------------------------------------------------------------------
# add_frontmatter
# ---------------------------------------------------------------------------


class TestAddFrontmatter:
    def test_noop_when_disabled(self, tmp_path, monkeypatch):
        monkeypatch.delenv("BUJO_OBSIDIAN_FRONTMATTER", raising=False)
        p = tmp_path / "test.md"
        p.write_text("t buy milk", encoding="utf-8")
        add_frontmatter(p, {"tags": "daily"})
        assert p.read_text() == "t buy milk"

    def test_creates_frontmatter_when_enabled(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_OBSIDIAN_FRONTMATTER", "1")
        p = tmp_path / "2026-03-16.md"
        p.write_text("t buy milk", encoding="utf-8")
        add_frontmatter(p, {"date": "2026-03-16", "tags": "daily"})
        content = p.read_text()
        assert content.startswith("---")
        assert "date: 2026-03-16" in content
        assert "tags: daily" in content
        assert "t buy milk" in content

    def test_merges_with_existing_frontmatter(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_OBSIDIAN_FRONTMATTER", "1")
        p = tmp_path / "2026-03-16.md"
        p.write_text("---\nauthor: Ryan\n---\nt buy milk", encoding="utf-8")
        add_frontmatter(p, {"date": "2026-03-16"})
        content = p.read_text()
        assert "author: Ryan" in content
        assert "date: 2026-03-16" in content
        assert "t buy milk" in content

    def test_does_not_overwrite_existing_keys(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_OBSIDIAN_FRONTMATTER", "1")
        p = tmp_path / "2026-03-16.md"
        p.write_text("---\ndate: old-date\n---\nt buy milk", encoding="utf-8")
        add_frontmatter(p, {"date": "new-date"})
        content = p.read_text()
        assert "old-date" in content
        assert "new-date" not in content

    def test_new_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_OBSIDIAN_FRONTMATTER", "1")
        p = tmp_path / "new.md"
        add_frontmatter(p, {"date": "2026-03-16"})
        content = p.read_text()
        assert content.startswith("---\n")
        assert "date: 2026-03-16" in content


# ---------------------------------------------------------------------------
# generate_dashboard
# ---------------------------------------------------------------------------


class TestGenerateDashboard:
    def test_noop_when_disabled(self, tmp_path, monkeypatch):
        monkeypatch.delenv("BUJO_DASHBOARD", raising=False)
        engine = MagicMock()
        generate_dashboard(tmp_path, engine)
        assert not (tmp_path / "dashboard.md").exists()

    def test_creates_dashboard_when_enabled(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_DASHBOARD", "1")
        engine = MagicMock()
        engine.full_report.return_value = {
            "streak": 5,
            "momentum": "building",
            "completion_rate_7d": 0.75,
            "nudge": "Keep going.",
            "stuck_tasks": [],
            "kill_themes": {},
        }
        generate_dashboard(tmp_path, engine)
        dashboard = tmp_path / "dashboard.md"
        assert dashboard.exists()
        content = dashboard.read_text()
        assert "# BuJo Dashboard" in content
        assert "5 days" in content
        assert "building" in content
        assert "75%" in content

    def test_dashboard_includes_stuck_tasks(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_DASHBOARD", "1")
        engine = MagicMock()
        engine.full_report.return_value = {
            "streak": 1,
            "momentum": "steady",
            "completion_rate_7d": 0.5,
            "nudge": "Focus.",
            "stuck_tasks": [
                {"text": "call dentist", "count": 5},
            ],
            "kill_themes": {"exercise": 3},
        }
        generate_dashboard(tmp_path, engine)
        content = (tmp_path / "dashboard.md").read_text()
        assert "Stuck Tasks" in content
        assert "call dentist" in content
        assert "Kill Themes" in content
        assert "exercise" in content
