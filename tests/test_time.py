"""Tests for bujo.time — time-aware utilities."""

from unittest.mock import patch

import pytest

from bujo.time import time_of_day_greeting, session_day_context, session_greeting


# ---------------------------------------------------------------------------
# time_of_day_greeting
# ---------------------------------------------------------------------------


class TestTimeOfDayGreeting:
    @patch("bujo.time.datetime")
    def test_morning(self, mock_dt):
        mock_dt.now.return_value.hour = 8
        assert "Morning" in time_of_day_greeting()

    @patch("bujo.time.datetime")
    def test_afternoon(self, mock_dt):
        mock_dt.now.return_value.hour = 14
        assert "Afternoon" in time_of_day_greeting()

    @patch("bujo.time.datetime")
    def test_evening(self, mock_dt):
        mock_dt.now.return_value.hour = 19
        assert "Evening" in time_of_day_greeting()

    @patch("bujo.time.datetime")
    def test_late(self, mock_dt):
        mock_dt.now.return_value.hour = 2
        assert "Late" in time_of_day_greeting()

    @patch("bujo.time.datetime")
    def test_boundary_5am(self, mock_dt):
        mock_dt.now.return_value.hour = 5
        assert "Morning" in time_of_day_greeting()

    @patch("bujo.time.datetime")
    def test_boundary_12pm(self, mock_dt):
        mock_dt.now.return_value.hour = 12
        assert "Afternoon" in time_of_day_greeting()

    @patch("bujo.time.datetime")
    def test_boundary_17(self, mock_dt):
        mock_dt.now.return_value.hour = 17
        assert "Evening" in time_of_day_greeting()

    @patch("bujo.time.datetime")
    def test_boundary_21(self, mock_dt):
        mock_dt.now.return_value.hour = 21
        assert "Evening" in time_of_day_greeting()  # 17 <= hour < 22

    @patch("bujo.time.datetime")
    def test_boundary_22(self, mock_dt):
        mock_dt.now.return_value.hour = 22
        assert "Late" in time_of_day_greeting()  # 21 <= hour or hour < 5


# ---------------------------------------------------------------------------
# session_day_context
# ---------------------------------------------------------------------------


class TestSessionDayContext:
    @patch("bujo.time.datetime")
    def test_monday(self, mock_dt):
        mock_dt.now.return_value.weekday.return_value = 0
        assert "priorities" in session_day_context()

    @patch("bujo.time.datetime")
    def test_friday(self, mock_dt):
        mock_dt.now.return_value.weekday.return_value = 4
        assert "migrate" in session_day_context()

    @patch("bujo.time.datetime")
    def test_tuesday(self, mock_dt):
        mock_dt.now.return_value.weekday.return_value = 1
        assert session_day_context() == ""


# ---------------------------------------------------------------------------
# session_greeting
# ---------------------------------------------------------------------------


class TestSessionGreeting:
    @patch("bujo.time.datetime")
    def test_morning_with_pending(self, mock_dt):
        mock_dt.now.return_value.hour = 9
        mock_dt.now.return_value.weekday.return_value = 2
        result = session_greeting(streak=1, pending_count=5)
        assert "Morning" in result
        assert "5 tasks" in result

    @patch("bujo.time.datetime")
    def test_morning_with_one_pending(self, mock_dt):
        mock_dt.now.return_value.hour = 9
        mock_dt.now.return_value.weekday.return_value = 2
        result = session_greeting(streak=1, pending_count=1)
        assert "1 task" in result  # singular

    @patch("bujo.time.datetime")
    def test_morning_clear_slate(self, mock_dt):
        mock_dt.now.return_value.hour = 9
        mock_dt.now.return_value.weekday.return_value = 2
        result = session_greeting(streak=1, pending_count=0)
        assert "Clear slate" in result

    @patch("bujo.time.datetime")
    def test_streak_acknowledgment(self, mock_dt):
        mock_dt.now.return_value.hour = 9
        mock_dt.now.return_value.weekday.return_value = 2
        result = session_greeting(streak=5, pending_count=0)
        assert "5-day streak" in result

    @patch("bujo.time.datetime")
    def test_no_streak_short(self, mock_dt):
        mock_dt.now.return_value.hour = 9
        mock_dt.now.return_value.weekday.return_value = 2
        result = session_greeting(streak=2, pending_count=0)
        assert "streak" not in result

    @patch("bujo.time.datetime")
    def test_monday_priorities_prompt(self, mock_dt):
        mock_dt.now.return_value.hour = 9
        mock_dt.now.return_value.weekday.return_value = 0
        result = session_greeting(streak=1, pending_count=0)
        assert "3 priorities" in result

    @patch("bujo.time.datetime")
    def test_friday_migration_prompt(self, mock_dt):
        mock_dt.now.return_value.hour = 9
        mock_dt.now.return_value.weekday.return_value = 4
        result = session_greeting(streak=1, pending_count=0)
        assert "migrate" in result.lower()

    @patch("bujo.time.datetime")
    def test_afternoon(self, mock_dt):
        mock_dt.now.return_value.hour = 14
        mock_dt.now.return_value.weekday.return_value = 2
        result = session_greeting(streak=1, pending_count=0)
        assert "Afternoon" in result

    @patch("bujo.time.datetime")
    def test_evening(self, mock_dt):
        mock_dt.now.return_value.hour = 19
        mock_dt.now.return_value.weekday.return_value = 2
        result = session_greeting(streak=1, pending_count=0)
        assert "Evening" in result

    @patch("bujo.time.datetime")
    def test_late(self, mock_dt):
        mock_dt.now.return_value.hour = 2
        mock_dt.now.return_value.weekday.return_value = 2
        result = session_greeting(streak=1, pending_count=0)
        assert "Late" in result

    @patch("bujo.time.datetime")
    def test_high_pending_triggers_triage(self, mock_dt):
        mock_dt.now.return_value.hour = 14
        mock_dt.now.return_value.weekday.return_value = 2  # not friday
        result = session_greeting(streak=1, pending_count=10)
        assert "triage" in result.lower()
