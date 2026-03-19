"""Tests for bujo.analytics — InsightsEngine."""

import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from bujo.analytics import InsightsEngine
from bujo.models import LogReader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_vault(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create a vault with daily files."""
    daily = tmp_path / "daily"
    daily.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (daily / name).write_text(content, encoding="utf-8")
    return tmp_path


def _make_log_content(*entries: str) -> str:
    return "\n".join(entries)


# ---------------------------------------------------------------------------
# kill_themes
# ---------------------------------------------------------------------------


class TestKillThemes:
    def test_groups_by_first_word(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-14.md": _make_log_content("k gym session"),
                "2026-03-15.md": _make_log_content("k gym workout", "k reading book"),
                "2026-03-16.md": _make_log_content("k reading novel"),
            },
        )
        engine = InsightsEngine(vault)
        themes = engine.kill_themes()
        assert themes.get("gym") == 2
        assert themes.get("reading") == 2

    def test_empty_when_no_killed(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": _make_log_content("t buy milk", "x done"),
            },
        )
        engine = InsightsEngine(vault)
        assert engine.kill_themes() == {}

    def test_returns_top_10(self, tmp_path):
        files = {}
        for i in range(15):
            d = date(2026, 3, 1) + timedelta(days=i)
            files[f"{d.isoformat()}.md"] = f"k task{i} something"
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        themes = engine.kill_themes()
        assert len(themes) <= 10


# ---------------------------------------------------------------------------
# done_pending_ratio
# ---------------------------------------------------------------------------


class TestDonePendingRatio:
    def test_all_done(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": _make_log_content("x done1", "x done2"),
            },
        )
        engine = InsightsEngine(vault)
        assert engine.done_pending_ratio(7) == 1.0

    def test_all_pending(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": _make_log_content("t task1", "t task2"),
            },
        )
        engine = InsightsEngine(vault)
        assert engine.done_pending_ratio(7) == 0.0

    def test_mixed(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": _make_log_content("x done", "t pending", "x done2"),
            },
        )
        engine = InsightsEngine(vault)
        assert engine.done_pending_ratio(7) == pytest.approx(2 / 3)

    def test_empty_vault(self, tmp_path):
        vault = _create_vault(tmp_path, {})
        engine = InsightsEngine(vault)
        assert engine.done_pending_ratio(7) == 0.0


# ---------------------------------------------------------------------------
# priority_alignment
# ---------------------------------------------------------------------------


class TestPriorityAlignment:
    def test_all_priorities_done(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": _make_log_content(
                    "* finish report",
                    "x finish report",
                    "* call dentist",
                    "x call dentist",
                ),
            },
        )
        engine = InsightsEngine(vault)
        assert engine.priority_alignment(7) == 1.0

    def test_no_priorities_done(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": _make_log_content(
                    "* finish report", "t something else"
                ),
            },
        )
        engine = InsightsEngine(vault)
        assert engine.priority_alignment(7) == 0.0

    def test_partial(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": _make_log_content(
                    "* priority1", "x priority1", "* priority2"
                ),
            },
        )
        engine = InsightsEngine(vault)
        assert engine.priority_alignment(7) == pytest.approx(0.5)

    def test_empty(self, tmp_path):
        vault = _create_vault(tmp_path, {})
        engine = InsightsEngine(vault)
        assert engine.priority_alignment(7) == 0.0


# ---------------------------------------------------------------------------
# streak
# ---------------------------------------------------------------------------


class TestStreak:
    def test_streak_of_3(self, tmp_path):
        today = date.today()
        files = {}
        for i in range(3):
            d = today - timedelta(days=i)
            files[f"{d.isoformat()}.md"] = "t task"
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        assert engine.streak() == 3

    def test_streak_broken(self, tmp_path):
        today = date.today()
        files = {}
        # Today and 2 days ago have entries, yesterday is missing
        files[f"{today.isoformat()}.md"] = "t task"
        d = today - timedelta(days=2)
        files[f"{d.isoformat()}.md"] = "t task"
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        assert engine.streak() == 1  # only today

    def test_no_entries(self, tmp_path):
        vault = _create_vault(tmp_path, {})
        engine = InsightsEngine(vault)
        assert engine.streak() == 0


# ---------------------------------------------------------------------------
# momentum_score
# ---------------------------------------------------------------------------


class TestMomentumScore:
    def test_new_vault(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": "t one",
            },
        )
        engine = InsightsEngine(vault)
        assert engine.momentum_score() == "new"

    def test_building(self, tmp_path):
        today = date.today()
        files = {}
        # Last week (days 7-13 ago): all pending (0% completion)
        for i in range(7, 14):
            d = today - timedelta(days=i)
            files[f"{d.isoformat()}.md"] = "t pending"
        # This week (days 0-6 ago): all done (100% completion)
        for i in range(7):
            d = today - timedelta(days=i)
            files[f"{d.isoformat()}.md"] = "x done"
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        assert engine.momentum_score() == "building"


# ---------------------------------------------------------------------------
# coaching_nudge
# ---------------------------------------------------------------------------


class TestCoachingNudge:
    def test_stuck_task_nudge(self, tmp_path):
        today = date.today()
        files = {}
        for i in range(5):
            d = today - timedelta(days=i)
            files[f"{d.isoformat()}.md"] = "> call dentist"
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        nudge = engine.coaching_nudge()
        assert "call dentist" in nudge
        assert "5" in nudge

    def test_streak_nudge(self, tmp_path):
        today = date.today()
        files = {}
        # Create 10 days with entries that won't trigger stuck/kill/priority nudges
        # Use varied text so no entry appears 3+ times as stuck
        for i in range(10):
            d = today - timedelta(days=i)
            entries = [
                f"x task{i}a",
                f"n note{i}b",
                f"* priority{i}c",  # priority entries
                f"x priority{i}c",  # same text done = priority alignment
            ]
            files[f"{d.isoformat()}.md"] = "\n".join(entries)
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        nudge = engine.coaching_nudge()
        assert "streak" in nudge.lower()

    def test_low_completion_nudge(self, tmp_path):
        today = date.today()
        files = {}
        # Last week: all pending
        for i in range(7, 14):
            d = today - timedelta(days=i)
            files[f"{d.isoformat()}.md"] = f"t pending task for day {i}"
        # This week: one priority done + more pending per day (low completion)
        for i in range(7):
            d = today - timedelta(days=i)
            files[f"{d.isoformat()}.md"] = (
                f"* important task{i}\n"
                f"x important task{i}\n"
                f"t pending task a{i}\n"
                f"t pending task b{i}"
            )
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        nudge = engine.coaching_nudge()
        # With 0% last week → 33% this week, momentum = "building"
        assert any(
            phrase in nudge.lower()
            for phrase in ["completion rate", "building", "keep going"]
        )


# ---------------------------------------------------------------------------
# full_report
# ---------------------------------------------------------------------------


class TestFullReport:
    def test_report_structure(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": _make_log_content("t buy milk", "x done"),
            },
        )
        engine = InsightsEngine(vault)
        report = engine.full_report()
        assert "period" in report
        assert "streak" in report
        assert "momentum" in report
        assert "completion_rate_7d" in report
        assert "priority_alignment_7d" in report
        assert "total_entries_7d" in report
        assert "stuck_tasks" in report
        assert "kill_themes" in report
        assert "nudge" in report
        assert "empty" in report
        assert "most_productive_time" in report
        assert "tasks_per_day_avg" in report

    def test_empty_report(self, tmp_path):
        vault = _create_vault(tmp_path, {})
        engine = InsightsEngine(vault)
        report = engine.full_report()
        assert report["empty"] is True

    def test_non_empty_report(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": _make_log_content("t buy milk", "x done", "n note"),
            },
        )
        engine = InsightsEngine(vault)
        report = engine.full_report()
        assert report["empty"] is False
        assert report["total_entries_7d"] == 3


# ---------------------------------------------------------------------------
# tasks_per_day_avg
# ---------------------------------------------------------------------------


class TestTasksPerDayAvg:
    def test_averages_done_tasks(self, tmp_path):
        today = date.today()
        files = {}
        # Day 1: 2 done, Day 2: 4 done
        d = today - timedelta(days=1)
        files[f"{d.isoformat()}.md"] = _make_log_content("x a", "x b")
        d2 = today - timedelta(days=2)
        files[f"{d2.isoformat()}.md"] = _make_log_content("x a", "x b", "x c", "x d")
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        avg = engine.tasks_per_day_avg()
        assert avg == pytest.approx(3.0)

    def test_excludes_empty_days(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": _make_log_content("x done"),
            },
        )
        engine = InsightsEngine(vault)
        avg = engine.tasks_per_day_avg()
        assert avg == 1.0  # not divided by 30

    def test_empty_vault(self, tmp_path):
        vault = _create_vault(tmp_path, {})
        engine = InsightsEngine(vault)
        assert engine.tasks_per_day_avg() == 0.0


# ---------------------------------------------------------------------------
# weekly_summary
# ---------------------------------------------------------------------------


class TestWeeklySummary:
    def test_summary_structure(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-16.md": _make_log_content(
                    "t task", "x done", "k killed", "> migrated"
                ),
            },
        )
        engine = InsightsEngine(vault)
        summary = engine.weekly_summary()
        assert "week_range" in summary
        assert summary["total_logged"] >= 4
        assert summary["total_done"] >= 1
        assert summary["total_killed"] >= 1
        assert summary["total_migrated"] >= 1
        assert "streak" in summary
        assert "top_insight" in summary
        assert "most_productive_time" in summary


# ---------------------------------------------------------------------------
# most_productive_time
# ---------------------------------------------------------------------------


class TestMostProductiveTime:
    def test_not_enough_data(self, tmp_path):
        vault = _create_vault(tmp_path, {})
        engine = InsightsEngine(vault)
        assert engine.most_productive_time() == "not enough data"

    def test_returns_bucket(self, tmp_path):
        today = date.today()
        files = {}
        for i in range(5):
            d = today - timedelta(days=i)
            files[f"{d.isoformat()}.md"] = _make_log_content("t task", "x done")
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        result = engine.most_productive_time()
        # Should return a bucket name (depends on file mtime)
        assert any(b in result for b in ["morning", "afternoon", "evening", "late"])


# ---------------------------------------------------------------------------
# stall_duration
# ---------------------------------------------------------------------------


class TestStallDuration:
    def test_task_with_history(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-10.md": _make_log_content("t gym session"),
                "2026-03-11.md": _make_log_content("t gym session"),
                "2026-03-12.md": _make_log_content("k 2026-03-12 gym session"),
            },
        )
        engine = InsightsEngine(vault)
        result = engine.stall_duration("2026-03-12 gym session")
        assert result == 2

    def test_task_never_seen_as_t(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-12.md": _make_log_content("k 2026-03-12 random idea"),
            },
        )
        engine = InsightsEngine(vault)
        result = engine.stall_duration("2026-03-12 random idea")
        assert result is None

    def test_killed_same_day_no_prior_t(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-12.md": _make_log_content("k 2026-03-12 quick drop"),
            },
        )
        engine = InsightsEngine(vault)
        result = engine.stall_duration("2026-03-12 quick drop")
        assert result is None


# ---------------------------------------------------------------------------
# stall_stats
# ---------------------------------------------------------------------------


class TestStallStats:
    def test_overall_stats(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-10.md": _make_log_content("t gym session"),
                "2026-03-12.md": _make_log_content("k 2026-03-12 gym session"),
                "2026-03-14.md": _make_log_content("t reading book"),
                "2026-03-17.md": _make_log_content("k 2026-03-17 reading book"),
            },
        )
        engine = InsightsEngine(vault)
        stats = engine.stall_stats()
        assert stats["count"] == 2
        assert stats["avg"] == 2.5
        assert stats["max"] == 3

    def test_filter_by_theme(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-10.md": _make_log_content("t gym session"),
                "2026-03-12.md": _make_log_content("k 2026-03-12 gym session"),
                "2026-03-14.md": _make_log_content("t reading book"),
                "2026-03-17.md": _make_log_content("k 2026-03-17 reading book"),
            },
        )
        engine = InsightsEngine(vault)
        gym_stats = engine.stall_stats(theme="gym")
        assert gym_stats["count"] == 1
        assert gym_stats["avg"] == 2.0

    def test_empty_vault(self, tmp_path):
        vault = _create_vault(tmp_path, {})
        engine = InsightsEngine(vault)
        stats = engine.stall_stats()
        assert stats == {"avg": 0.0, "median": 0.0, "max": 0, "count": 0}

    def test_no_kill_dates(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-12.md": _make_log_content("k just dropped"),
            },
        )
        engine = InsightsEngine(vault)
        stats = engine.stall_stats()
        assert stats["count"] == 0


# ---------------------------------------------------------------------------
# event_density_mapping
# ---------------------------------------------------------------------------


class TestEventDensityMapping:
    def test_buckets_reflect_event_counts(self, tmp_path):
        today = date.today()
        files = {}
        d0 = today - timedelta(days=0)
        d1 = today - timedelta(days=1)
        files[f"{d0.isoformat()}.md"] = _make_log_content("t task")
        files[f"{d1.isoformat()}.md"] = _make_log_content("t task", "e meeting", "x done")
        d2 = today - timedelta(days=2)
        files[f"{d2.isoformat()}.md"] = _make_log_content(
            "e meeting", "e dinner", "t task", "x done"
        )
        d3 = today - timedelta(days=3)
        files[f"{d3.isoformat()}.md"] = _make_log_content(
            "e a", "e b", "e c", "e d", "t task"
        )
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        result = engine.event_density_mapping()
        # All 30 days are bucketed; only the 4 days with files matter
        # day 0: 0 events → low, day 1: 1 event → low, day 2: 2 events → medium, day 3: 4 events → high
        assert result["high"]["completion_rate"] == 0.0

    def test_empty_vault_returns_low_bucket(self, tmp_path):
        vault = _create_vault(tmp_path, {})
        engine = InsightsEngine(vault)
        result = engine.event_density_mapping()
        # All 30 days have 0 events → all low
        assert result["low"]["days"] == 30


# ---------------------------------------------------------------------------
# event_heavy_day_nudge
# ---------------------------------------------------------------------------


class TestEventHeavyDayNudge:
    def test_triggers_on_3plus_events_zero_done(self, tmp_path):
        today = date.today()
        files = {}
        d = today - timedelta(days=1)
        files[f"{d.isoformat()}.md"] = _make_log_content(
            "e meeting", "e lunch", "e dinner", "t pending"
        )
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        nudge = engine.event_heavy_day_nudge()
        assert nudge is not None
        assert "overcommit" in nudge.lower()

    def test_no_nudge_when_done_exists(self, tmp_path):
        today = date.today()
        files = {}
        d = today - timedelta(days=1)
        files[f"{d.isoformat()}.md"] = _make_log_content(
            "e meeting", "e lunch", "x done"
        )
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        nudge = engine.event_heavy_day_nudge()
        assert nudge is None


# ---------------------------------------------------------------------------
# note_density
# ---------------------------------------------------------------------------


class TestNoteDensity:
    def test_note_counts_and_heavy_flag(self, tmp_path):
        today = date.today()
        files = {}
        d1 = today - timedelta(days=0)
        d2 = today - timedelta(days=1)
        files[f"{d1.isoformat()}.md"] = _make_log_content(
            "n note1", "n note2", "n note3", "n note4", "n note5", "t task"
        )
        files[f"{d2.isoformat()}.md"] = _make_log_content("n note1", "t task")
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        result = engine.note_density()
        heavy = [r for r in result if r["heavy"]]
        assert len(heavy) == 1

    def test_empty_vault(self, tmp_path):
        vault = _create_vault(tmp_path, {})
        engine = InsightsEngine(vault)
        result = engine.note_density()
        assert len(result) == 14


# ---------------------------------------------------------------------------
# note_heavy_days
# ---------------------------------------------------------------------------


class TestNoteHeavyDays:
    def test_returns_heavy_days_sorted(self, tmp_path):
        today = date.today()
        files = {}
        d1 = today - timedelta(days=0)
        d2 = today - timedelta(days=1)
        d3 = today - timedelta(days=2)
        files[f"{d1.isoformat()}.md"] = _make_log_content(
            "n a", "n b", "n c", "n d", "n e"
        )
        files[f"{d2.isoformat()}.md"] = _make_log_content(
            "n a", "n b", "n c", "n d", "n e", "n f", "n g"
        )
        files[f"{d3.isoformat()}.md"] = _make_log_content("n one")
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        heavy = engine.note_heavy_days()
        assert len(heavy) == 2
        assert heavy[0]["count"] == 7
        assert heavy[1]["count"] == 5


# ---------------------------------------------------------------------------
# coaching_nudge — event overcommit and note dump
# ---------------------------------------------------------------------------


class TestCoachingNudgeNewBranches:
    def test_event_overcommit_nudge(self, tmp_path):
        today = date.today()
        files = {}
        for i in range(3):
            d = today - timedelta(days=i)
            entries = ["e a", "e b", "e c", "t pending"]
            files[f"{d.isoformat()}.md"] = "\n".join(entries)
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        nudge = engine.coaching_nudge()
        assert "overcommit" in nudge.lower()

    def test_note_dump_nudge(self, tmp_path):
        today = date.today()
        files = {}
        for i in range(3):
            d = today - timedelta(days=i)
            notes = "\n".join([f"n note{j}" for j in range(6)])
            files[f"{d.isoformat()}.md"] = notes
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        nudge = engine.coaching_nudge()
        assert "note" in nudge.lower() or "dump" in nudge.lower()

    def test_stall_duration_in_nudge(self, tmp_path):
        vault = _create_vault(
            tmp_path,
            {
                "2026-03-10.md": _make_log_content("t gym session"),
                "2026-03-11.md": _make_log_content("t gym session"),
                "2026-03-12.md": _make_log_content("k 2026-03-12 gym session"),
                "2026-03-13.md": _make_log_content("t gym session"),
                "2026-03-14.md": _make_log_content("k 2026-03-14 gym session"),
                "2026-03-15.md": _make_log_content("t gym session"),
                "2026-03-16.md": _make_log_content("k 2026-03-16 gym session"),
            },
        )
        engine = InsightsEngine(vault)
        nudge = engine.coaching_nudge()
        assert "gym" in nudge.lower()


# ---------------------------------------------------------------------------
# full_report — new keys
# ---------------------------------------------------------------------------


class TestFullReportNewKeys:
    def test_includes_stall_and_event_keys(self, tmp_path):
        today = date.today()
        files = {}
        d = today - timedelta(days=0)
        files[f"{d.isoformat()}.md"] = _make_log_content("t task", "x done")
        vault = _create_vault(tmp_path, files)
        engine = InsightsEngine(vault)
        report = engine.full_report()
        assert "avg_stall_days" in report
        assert "event_density_mapping" in report
        assert "note_heavy_days_14d" in report

    def test_event_density_mapping_structure(self, tmp_path):
        vault = _create_vault(tmp_path, {})
        engine = InsightsEngine(vault)
        report = engine.full_report()
        mapping = report["event_density_mapping"]
        assert "low" in mapping
        assert "medium" in mapping
        assert "high" in mapping
        assert "days" in mapping["low"]
        assert "completion_rate" in mapping["low"]
