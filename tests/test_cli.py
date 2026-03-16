"""Tests for bujo.cli — CLI commands via subprocess."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def _run_cli(*args: str, vault: str | None = None) -> subprocess.CompletedProcess:
    """Run the CLI as a subprocess with BUJO_VAULT set."""
    env = os.environ.copy()
    if vault:
        env["BUJO_VAULT"] = vault
    else:
        tmp = tempfile.mkdtemp()
        env["BUJO_VAULT"] = tmp
    return subprocess.run(
        [sys.executable, "-m", "bujo.cli"] + list(args),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
        cwd=str(Path(__file__).parent.parent),
    )


# ---------------------------------------------------------------------------
# help
# ---------------------------------------------------------------------------


class TestCLIHelp:
    def test_no_args_shows_doc(self):
        result = _run_cli("--help")
        assert result.returncode == 0
        assert "Usage:" in result.stdout

    def test_help_command(self):
        result = _run_cli("help")
        assert result.returncode == 0
        assert "Usage:" in result.stdout


# ---------------------------------------------------------------------------
# vault
# ---------------------------------------------------------------------------


class TestCLIVault:
    def test_vault_command(self, tmp_path):
        result = _run_cli("vault", vault=str(tmp_path))
        assert result.returncode == 0
        assert str(tmp_path) in result.stdout


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


class TestCLIAdd:
    def test_add_task(self, tmp_path):
        result = _run_cli("add", "t", "buy milk", vault=str(tmp_path))
        assert result.returncode == 0
        assert "buy milk" in result.stdout
        # Verify file was created
        daily = tmp_path / "daily"
        from datetime import date

        today_file = daily / f"{date.today().isoformat()}.md"
        assert today_file.exists()
        content = today_file.read_text()
        assert "t buy milk" in content

    def test_add_note(self, tmp_path):
        result = _run_cli("add", "n", "feeling good", vault=str(tmp_path))
        assert result.returncode == 0
        assert "feeling good" in result.stdout

    def test_add_priority(self, tmp_path):
        result = _run_cli("add", "*", "urgent task", vault=str(tmp_path))
        assert result.returncode == 0
        assert "urgent task" in result.stdout

    def test_add_event(self, tmp_path):
        result = _run_cli("add", "e", "meeting at 3", vault=str(tmp_path))
        assert result.returncode == 0

    def test_add_done(self, tmp_path):
        result = _run_cli("add", "x", "completed task", vault=str(tmp_path))
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# capture
# ---------------------------------------------------------------------------


class TestCLICapture:
    def test_capture_note(self, tmp_path):
        result = _run_cli("capture", "note: feeling great", vault=str(tmp_path))
        assert result.returncode == 0
        assert "feeling great" in result.stdout

    def test_capture_priority(self, tmp_path):
        result = _run_cli("capture", "urgent task!", vault=str(tmp_path))
        assert result.returncode == 0

    def test_capture_done(self, tmp_path):
        result = _run_cli("capture", "done: wrote tests", vault=str(tmp_path))
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# log
# ---------------------------------------------------------------------------


class TestCLILog:
    def test_log_empty_vault(self, tmp_path):
        result = _run_cli("log", vault=str(tmp_path))
        assert result.returncode == 0

    def test_log_with_entries(self, tmp_path):
        # First add an entry
        _run_cli("add", "t", "buy milk", vault=str(tmp_path))
        result = _run_cli("log", vault=str(tmp_path))
        assert result.returncode == 0
        assert "buy milk" in result.stdout


# ---------------------------------------------------------------------------
# coach
# ---------------------------------------------------------------------------


class TestCLICoach:
    def test_coach_json(self, tmp_path):
        _run_cli("add", "t", "task1", vault=str(tmp_path))
        result = _run_cli("coach", vault=str(tmp_path))
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "streak" in data
        assert "momentum" in data

    def test_coach_human(self, tmp_path):
        # Need at least 3 entries for non-empty report
        _run_cli("add", "t", "task1", vault=str(tmp_path))
        _run_cli("add", "x", "done1", vault=str(tmp_path))
        _run_cli("add", "n", "note1", vault=str(tmp_path))
        result = _run_cli("coach", "--human", vault=str(tmp_path))
        assert result.returncode == 0
        assert "Momentum" in result.stdout


# ---------------------------------------------------------------------------
# streak
# ---------------------------------------------------------------------------


class TestCLIStreak:
    def test_streak_zero(self, tmp_path):
        result = _run_cli("streak", vault=str(tmp_path))
        assert result.returncode == 0
        assert "No streak" in result.stdout

    def test_streak_one(self, tmp_path):
        _run_cli("add", "t", "task1", vault=str(tmp_path))
        result = _run_cli("streak", vault=str(tmp_path))
        assert result.returncode == 0
        assert "1 day" in result.stdout


# ---------------------------------------------------------------------------
# week
# ---------------------------------------------------------------------------


class TestCLIWeek:
    def test_week_command(self, tmp_path):
        _run_cli("add", "t", "task1", vault=str(tmp_path))
        result = _run_cli("week", vault=str(tmp_path))
        assert result.returncode == 0
        assert "Logged" in result.stdout


# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------


class TestCLITemplate:
    def test_template_morning(self, tmp_path):
        result = _run_cli("template", "morning", vault=str(tmp_path))
        assert result.returncode == 0
        assert "Applied template" in result.stdout

    def test_template_nonexistent(self, tmp_path):
        result = _run_cli("template", "nonexistent", vault=str(tmp_path))
        assert result.returncode == 0
        assert "not found" in result.stdout


# ---------------------------------------------------------------------------
# insights
# ---------------------------------------------------------------------------


class TestCLIInsights:
    def test_insights_empty(self, tmp_path):
        result = _run_cli("insights", vault=str(tmp_path))
        assert result.returncode == 0
        assert "Not enough data" in result.stdout

    def test_insights_with_data(self, tmp_path):
        # Need at least 3 entries for non-empty report
        _run_cli("add", "t", "task1", vault=str(tmp_path))
        _run_cli("add", "x", "done1", vault=str(tmp_path))
        _run_cli("add", "n", "note1", vault=str(tmp_path))
        result = _run_cli("insights", vault=str(tmp_path))
        assert result.returncode == 0
        assert "Momentum" in result.stdout


# ---------------------------------------------------------------------------
# unknown command
# ---------------------------------------------------------------------------


class TestCLIUnknown:
    def test_unknown_command(self, tmp_path):
        result = _run_cli("bogus", vault=str(tmp_path))
        assert result.returncode == 1
        assert "Unknown command" in result.stdout
