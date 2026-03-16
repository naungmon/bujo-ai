"""Tests for bujo.capture — NLP parsing and templates."""

import pytest

from bujo.capture import parse_quick_input, detect_type


# ---------------------------------------------------------------------------
# parse_quick_input
# ---------------------------------------------------------------------------


class TestParseQuickInput:
    # Rule 1: note prefix
    def test_note_colon(self):
        assert parse_quick_input("note: feeling good") == ("n", "feeling good")

    def test_note_n_prefix(self):
        assert parse_quick_input("n: feeling good") == ("n", "feeling good")

    def test_note_case_insensitive(self):
        assert parse_quick_input("NOTE: feeling good") == ("n", "feeling good")

    # Rule 2: event prefix
    def test_event_colon(self):
        assert parse_quick_input("event: meeting at 3pm") == ("e", "meeting at 3pm")

    def test_event_e_prefix(self):
        assert parse_quick_input("e: meeting at 3pm") == ("e", "meeting at 3pm")

    # Rule 3: done prefix
    def test_done_colon(self):
        assert parse_quick_input("done: wrote tests") == ("x", "wrote tests")

    def test_done_space(self):
        assert parse_quick_input("done wrote tests") == ("x", "wrote tests")

    # Rule 4: exclamation mark
    def test_exclamation_end(self):
        assert parse_quick_input("finish the report!") == ("*", "finish the report")

    def test_exclamation_start(self):
        assert parse_quick_input("! urgent task") == ("*", "urgent task")

    # Rule 5: important/urgent keywords
    def test_important_keyword(self):
        assert parse_quick_input("fix bug important") == ("*", "fix bug")

    def test_urgent_keyword(self):
        assert parse_quick_input("send email urgent") == ("*", "send email")

    # Rule 6: default (task)
    def test_default_task(self):
        assert parse_quick_input("buy milk") == ("t", "buy milk")

    def test_default_long_text(self):
        assert parse_quick_input("go to the store and buy some milk") == (
            "t",
            "go to the store and buy some milk",
        )

    # Rule 1: note prefix (space variant)
    def test_note_space(self):
        assert parse_quick_input("note feeling good") == ("n", "feeling good")

    # Rule 2: event prefix (space variant)
    def test_event_space(self):
        assert parse_quick_input("event tomorrow at 3") == ("e", "tomorrow at 3")

    # Rule 6: priority prefix
    def test_priority_word(self):
        assert parse_quick_input("priority finish report") == ("*", "finish report")

    def test_priority_p_prefix(self):
        assert parse_quick_input("p finish report") == ("*", "finish report")

    # Rule 7: task prefix
    def test_task_word(self):
        assert parse_quick_input("task call jackson") == ("t", "call jackson")

    def test_task_short(self):
        assert parse_quick_input("t buy milk") == ("t", "buy milk")

    # Edge cases
    def test_empty_string(self):
        assert parse_quick_input("") == ("t", "")

    def test_whitespace_only(self):
        assert parse_quick_input("   ") == ("t", "")

    def test_priority_takes_precedence_over_default(self):
        """Exclamation should win over default task."""
        assert parse_quick_input("do this!") == ("*", "do this")

    def test_done_takes_precedence_over_exclamation(self):
        """done: prefix should be checked before ! since done is rule 3, ! is rule 4."""
        assert parse_quick_input("done: write report!") == ("x", "write report!")

    def test_note_takes_precedence_over_default(self):
        assert parse_quick_input("note: buy milk") == ("n", "buy milk")


# ---------------------------------------------------------------------------
# detect_type
# ---------------------------------------------------------------------------


class TestDetectType:
    def test_detect_task(self):
        assert detect_type("buy milk") == ("t", "Task")

    def test_detect_note(self):
        assert detect_type("note: feeling good") == ("n", "Note")

    def test_detect_priority(self):
        assert detect_type("urgent!") == ("*", "Priority")

    def test_detect_done(self):
        assert detect_type("done: wrote tests") == ("x", "Done")

    def test_detect_event(self):
        assert detect_type("event: meeting at 3") == ("e", "Event")
