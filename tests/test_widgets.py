"""Tests for BuJo widgets — DateRibbon, BuJoListView, EntryItem, BuJoInput."""

from datetime import date, timedelta

import pytest

from bujo.widgets.date_ribbon import DateRibbon


class TestDateRibbon:
    def test_go_prev_decrements(self):
        ribbon = DateRibbon()
        ribbon.viewing_date = date(2026, 3, 17)
        ribbon.go_prev()
        assert ribbon.viewing_date == date(2026, 3, 16)

    def test_go_next_increments(self):
        ribbon = DateRibbon()
        ribbon.viewing_date = date(2026, 3, 16)
        ribbon.go_next()
        assert ribbon.viewing_date == date(2026, 3, 17)

    def test_go_next_allows_future(self):
        """Spec says future days show as empty, so navigation must not be blocked."""
        ribbon = DateRibbon()
        ribbon.viewing_date = date.today()
        ribbon.go_next()
        assert ribbon.viewing_date == date.today() + timedelta(days=1)

    def test_is_viewing_today(self):
        ribbon = DateRibbon()
        ribbon.viewing_date = date.today()
        assert ribbon.is_viewing_today
        ribbon.go_prev()
        assert not ribbon.is_viewing_today
