"""Tests for bujo.models — entry parsing, DayLog, LogReader."""

import os
import tempfile
from datetime import date
from pathlib import Path

import pytest

from bujo.models import (
    Entry,
    DayLog,
    LogReader,
    SYMBOLS,
    SYMBOL_DISPLAY,
    LEGACY_UNICODE_TO_ASCII,
    parse_entries,
    read_text_safe,
)


# ---------------------------------------------------------------------------
# parse_entries — ASCII format
# ---------------------------------------------------------------------------


class TestParseEntriesASCII:
    def _parse(self, content: str) -> list[Entry]:
        p = Path("test.md")
        return parse_entries(content, p, date(2026, 3, 16))

    def test_task(self):
        entries = self._parse("t buy milk")
        assert len(entries) == 1
        assert entries[0].symbol == "t"
        assert entries[0].text == "buy milk"
        assert entries[0].type == "Task"

    def test_done(self):
        entries = self._parse("x wrote tests")
        assert entries[0].symbol == "x"
        assert entries[0].type == "Done"

    def test_migrated(self):
        entries = self._parse("> call dentist")
        assert entries[0].symbol == ">"

    def test_scheduled_less_than(self):
        entries = self._parse("< call dentist")
        assert entries[0].symbol == "<"
        assert entries[0].text == "call dentist"
        assert entries[0].type == "Scheduled"

    def test_killed(self):
        entries = self._parse("k old project")
        assert entries[0].symbol == "k"

    def test_note(self):
        entries = self._parse("n feeling focused")
        assert entries[0].symbol == "n"
        assert entries[0].type == "Note"

    def test_event(self):
        entries = self._parse("e meeting at 3pm")
        assert entries[0].symbol == "e"
        assert entries[0].type == "Event"

    def test_priority(self):
        entries = self._parse("* finish report")
        assert entries[0].symbol == "*"
        assert entries[0].type == "Priority"

    def test_multiple_entries(self):
        content = "t buy milk\nx wrote tests\n* urgent thing"
        entries = self._parse(content)
        assert len(entries) == 3
        assert entries[0].symbol == "t"
        assert entries[1].symbol == "x"
        assert entries[2].symbol == "*"

    def test_empty_lines_skipped(self):
        content = "t buy milk\n\n\nx wrote tests"
        entries = self._parse(content)
        assert len(entries) == 2

    def test_comments_skipped(self):
        content = "# Heading\nt buy milk\n## Another heading"
        entries = self._parse(content)
        assert len(entries) == 1

    def test_whitespace_preserved_in_text(self):
        entries = self._parse("t buy   milk   now")
        assert entries[0].text == "buy   milk   now"

    def test_no_match_returns_empty(self):
        entries = self._parse("just some random text")
        assert entries == []

    def test_display_matches_unicode(self):
        entries = self._parse("t buy milk")
        assert entries[0].display == SYMBOL_DISPLAY["t"]

    def test_raw_stores_original_line(self):
        entries = self._parse("t buy milk")
        assert entries[0].raw == "t buy milk"

    def test_source_file_and_date(self):
        p = Path("daily/2026-03-16.md")
        d = date(2026, 3, 16)
        entries = self._parse("t buy milk")
        # The function receives source_file and file_date — verify they are
        # stored via the calling pattern used by LogReader
        p2 = Path("test.md")
        entries = parse_entries("t buy milk", p2, d)
        assert entries[0].source_file == p2
        assert entries[0].date == d


# ---------------------------------------------------------------------------
# parse_entries — legacy Unicode format
# ---------------------------------------------------------------------------


class TestParseEntriesUnicode:
    def _parse(self, content: str) -> list[Entry]:
        p = Path("test.md")
        return parse_entries(content, p, date(2026, 3, 16))

    def test_unicode_task(self):
        entries = self._parse("\u00b7 buy milk")  # ·
        assert len(entries) == 1
        assert entries[0].symbol == "t"

    def test_unicode_done(self):
        entries = self._parse("\u00d7 wrote tests")  # ×
        assert entries[0].symbol == "x"

    def test_unicode_note(self):
        entries = self._parse("\u2013 feeling good")  # –
        assert entries[0].symbol == "n"

    def test_unicode_event(self):
        entries = self._parse("\u25cb meeting at 3")  # ○
        assert entries[0].symbol == "e"

    def test_unicode_priority(self):
        entries = self._parse("\u2605 urgent")  # ★
        assert entries[0].symbol == "*"

    def test_unicode_tilde_killed(self):
        entries = self._parse("~ old project")
        assert entries[0].symbol == "k"

    def test_mixed_ascii_unicode(self):
        content = "t buy milk\n\u00d7 wrote tests\n\u2605 urgent"
        entries = self._parse(content)
        assert len(entries) == 3
        assert entries[0].symbol == "t"
        assert entries[1].symbol == "x"
        assert entries[2].symbol == "*"


# ---------------------------------------------------------------------------
# DayLog properties
# ---------------------------------------------------------------------------


class TestDayLog:
    def _entry(self, symbol: str, text: str = "test") -> Entry:
        return Entry(
            symbol=symbol,
            display=SYMBOL_DISPLAY.get(symbol, symbol),
            text=text,
            type=SYMBOLS.get(symbol, ("Unknown", ""))[0],
            raw=f"{symbol} {text}",
            source_file=Path("test.md"),
            date=date(2026, 3, 16),
        )

    def test_done_property(self):
        log = DayLog(
            date=date.today(),
            path=Path("."),
            entries=[
                self._entry("x", "done task"),
                self._entry("t", "pending task"),
                self._entry("x", "another done"),
            ],
        )
        assert len(log.done) == 2

    def test_pending_property(self):
        log = DayLog(
            date=date.today(),
            path=Path("."),
            entries=[
                self._entry("t", "pending"),
                self._entry("x", "done"),
            ],
        )
        assert len(log.pending) == 1

    def test_priorities_property(self):
        log = DayLog(
            date=date.today(),
            path=Path("."),
            entries=[
                self._entry("*", "priority"),
                self._entry("t", "task"),
            ],
        )
        assert len(log.priorities) == 1

    def test_killed_property(self):
        log = DayLog(
            date=date.today(),
            path=Path("."),
            entries=[
                self._entry("k", "killed"),
            ],
        )
        assert len(log.killed) == 1

    def test_migrated_property(self):
        log = DayLog(
            date=date.today(),
            path=Path("."),
            entries=[
                self._entry(">", "migrated"),
            ],
        )
        assert len(log.migrated) == 1

    def test_scheduled_property(self):
        log = DayLog(
            date=date.today(),
            path=Path("."),
            entries=[
                self._entry("<", "from future"),
                self._entry("t", "task"),
                self._entry("<", "another scheduled"),
            ],
        )
        assert len(log.scheduled) == 2
        assert log.scheduled[0].text == "from future"
        assert log.scheduled[1].text == "another scheduled"

    def test_events_property(self):
        log = DayLog(
            date=date.today(),
            path=Path("."),
            entries=[
                self._entry("e", "meeting at 3pm"),
                self._entry("t", "task"),
                self._entry("e", "dinner"),
            ],
        )
        assert len(log.events) == 2
        assert log.events[0].text == "meeting at 3pm"
        assert log.events[1].text == "dinner"

    def test_completion_rate_full(self):
        log = DayLog(
            date=date.today(),
            path=Path("."),
            entries=[
                self._entry("x", "done"),
                self._entry("x", "done2"),
                self._entry("t", "pending"),
            ],
        )
        assert log.completion_rate == pytest.approx(2 / 3)

    def test_completion_rate_empty(self):
        log = DayLog(date=date.today(), path=Path("."), entries=[])
        assert log.completion_rate == 0.0

    def test_completion_rate_all_done(self):
        log = DayLog(
            date=date.today(),
            path=Path("."),
            entries=[
                self._entry("x", "done"),
                self._entry("x", "done2"),
            ],
        )
        assert log.completion_rate == 1.0


# ---------------------------------------------------------------------------
# read_text_safe
# ---------------------------------------------------------------------------


class TestReadTextSafe:
    def test_utf8_file(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("t buy milk\nx done", encoding="utf-8")
        assert read_text_safe(p) == "t buy milk\nx done"

    def test_missing_file(self, tmp_path):
        p = tmp_path / "nonexistent.md"
        assert read_text_safe(p) == ""

    def test_cp1252_fallback(self, tmp_path):
        p = tmp_path / "legacy.md"
        # \x80 (€) and \x8a (Š) are valid cp1252 but not valid UTF-8
        p.write_bytes(b"\x80\x8a t buy milk")
        result = read_text_safe(p)
        assert "buy milk" in result


# ---------------------------------------------------------------------------
# LogReader
# ---------------------------------------------------------------------------


class TestLogReader:
    def _create_vault(self, tmp_path, files: dict[str, str]) -> Path:
        daily = tmp_path / "daily"
        daily.mkdir(parents=True)
        for name, content in files.items():
            (daily / name).write_text(content, encoding="utf-8")
        return tmp_path

    def test_load_day_existing(self, tmp_path):
        vault = self._create_vault(tmp_path, {"2026-03-16.md": "t buy milk\nx done"})
        reader = LogReader(vault)
        log = reader.load_day(date(2026, 3, 16))
        assert len(log.entries) == 2
        assert log.entries[0].symbol == "t"
        assert log.entries[1].symbol == "x"

    def test_load_day_missing(self, tmp_path):
        vault = self._create_vault(tmp_path, {})
        reader = LogReader(vault)
        log = reader.load_day(date(2026, 3, 16))
        assert len(log.entries) == 0
        assert log.path == vault / "daily" / "2026-03-16.md"

    def test_load_range_skips_missing(self, tmp_path):
        from datetime import date, timedelta
        vault = self._create_vault(tmp_path, {})
        today = date.today()
        recent_file = (today - timedelta(days=1)).isoformat()
        (vault / "daily" / f"{recent_file}.md").write_text("t buy milk\n", encoding="utf-8")
        reader = LogReader(vault)
        logs = reader.load_range(3)
        assert len(logs) == 3
        total_entries = sum(len(l.entries) for l in logs)
        assert total_entries == 1

    def test_load_all_sorted_oldest_first(self, tmp_path):
        vault = self._create_vault(
            tmp_path,
            {
                "2026-03-16.md": "t today",
                "2026-03-14.md": "t two days ago",
                "2026-03-15.md": "t yesterday",
            },
        )
        reader = LogReader(vault)
        logs = reader.load_all()
        assert len(logs) == 3
        assert logs[0].date == date(2026, 3, 14)
        assert logs[2].date == date(2026, 3, 16)

    def test_load_all_skips_invalid_filenames(self, tmp_path):
        vault = self._create_vault(
            tmp_path,
            {
                "2026-03-16.md": "t valid",
                "not-a-date.md": "t invalid",
            },
        )
        reader = LogReader(vault)
        logs = reader.load_all()
        assert len(logs) == 1
        assert logs[0].date == date(2026, 3, 16)

    def test_load_all_empty_daily_dir(self, tmp_path):
        daily = tmp_path / "daily"
        daily.mkdir(parents=True)
        reader = LogReader(tmp_path)
        assert reader.load_all() == []
