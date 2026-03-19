"""Tests for bujo.views.future — month-grouped future log."""

import pytest


class TestFutureViewMonthDetection:
    def _detect_month(self, text: str) -> str | None:
        from bujo.views.future import FutureView
        fv = FutureView()
        return fv._detect_month(text)

    def test_detects_month_name_lowercase(self):
        result = self._detect_month("call dentist june")
        assert result == "June 2026"

    def test_detects_month_name_capitalized(self):
        result = self._detect_month("call dentist June")
        assert result == "June 2026"

    def test_detects_august(self):
        result = self._detect_month("august trip to thailand")
        assert result == "August 2026"

    def test_detects_month_with_colon(self):
        result = self._detect_month("September: renew visa")
        assert result == "September 2026"

    def test_detects_year_suffix(self):
        result = self._detect_month("june 2027 dentist")
        assert result == "June 2027"

    def test_no_month_returns_none(self):
        result = self._detect_month("just a task")
        assert result is None

    def test_past_month_defaults_to_next_year(self):
        from datetime import date
        result = self._detect_month("january dentist")
        year = date.today().year
        expected_year = year + 1
        assert result == f"January {expected_year}"

    def test_current_month_stays_current_year(self):
        from datetime import date
        month_name = date.today().strftime("%B").lower()
        result = self._detect_month(f"call dentist {month_name}")
        assert result == f"{date.today().strftime('%B')} {date.today().year}"
