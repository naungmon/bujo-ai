"""Tests for bujo.ai_capture — TUI-side AI smart_parse (mocked API)."""

import os
from unittest.mock import patch, MagicMock

import pytest

from bujo.ai_capture import has_explicit_prefix, smart_parse, ai_parse_dump


class TestHasExplicitPrefix:
    def test_single_char_prefix(self):
        assert has_explicit_prefix("t buy milk")
        assert has_explicit_prefix("n feeling good")
        assert has_explicit_prefix("e meeting at 3")
        assert has_explicit_prefix("k that idea")
        assert has_explicit_prefix("x done")
        assert has_explicit_prefix("> migrated")
        assert has_explicit_prefix("* priority")

    def test_word_prefix(self):
        assert has_explicit_prefix("task buy milk")
        assert has_explicit_prefix("note feeling good")
        assert has_explicit_prefix("event meeting at 3")
        assert has_explicit_prefix("priority finish report")
        assert has_explicit_prefix("done wrote tests")
        assert has_explicit_prefix("kill that idea")

    def test_exclamation_shorthand(self):
        assert has_explicit_prefix("! fix this")
        assert has_explicit_prefix("finish this!")

    def test_no_prefix(self):
        assert not has_explicit_prefix("buy milk")
        assert not has_explicit_prefix("feeling scattered today")
        assert not has_explicit_prefix("call jackson")


class TestSmartParseWithPrefix:
    @patch("bujo.ai_capture.ai_parse_dump")
    def test_explicit_prefix_uses_parse_quick_input(self, mock_ai):
        from bujo.capture import parse_quick_input
        result = smart_parse("t buy milk and n feeling good")
        assert len(result) == 1
        sym, text = result[0]
        assert sym == "t"
        assert "buy milk" in text
        mock_ai.assert_not_called()

    @patch("bujo.ai_capture.ai_parse_dump")
    def test_exclamation_becomes_priority(self, mock_ai):
        result = smart_parse("finish this report!")
        assert len(result) == 1
        assert result[0][0] == "*"


class TestSmartParseFallback:
    @patch("bujo.ai_capture.ai_parse_dump")
    def test_no_prefix_falls_back_to_ai(self, mock_ai):
        mock_ai.return_value = [("t", "buy milk"), ("n", "feeling scattered")]
        result = smart_parse("buy milk and feeling scattered")
        mock_ai.assert_called_once()
        assert len(result) == 2

    @patch("bujo.ai_capture.ai_parse_dump")
    def test_ai_failure_falls_back_to_note(self, mock_ai):
        mock_ai.return_value = None
        result = smart_parse("unparsed freeform text")
        assert result == [("n", "unparsed freeform text")]

    def test_empty_text_returns_empty(self):
        result = smart_parse("")
        assert result == []


class TestPromptCompleteness:
    def test_system_prompt_teaches_all_symbols(self):
        """SYSTEM_PROMPT must mention all actionable BuJo symbols."""
        from bujo.ai_capture import SYSTEM_PROMPT
        # These symbols should be taught to the AI
        for sym in ["t", "n", "e", "*", "k", "x", ">"]:
            assert sym in SYSTEM_PROMPT, f"SYSTEM_PROMPT missing symbol: {sym}"


class TestAIParseDump:
    def test_no_key_returns_none(self):
        import bujo.ai_capture as m
        m.OPENROUTER_API_KEY = ""
        try:
            result = ai_parse_dump("test")
            assert result is None
        finally:
            m.OPENROUTER_API_KEY = os.environ.get("BUJO_AI_KEY") or os.environ.get("OPENROUTER_API_KEY", "")

    def test_rate_limited_returns_none(self):
        import bujo.ai_capture as m
        from bujo.rate_limit import get_ai_limiter
        limiter = get_ai_limiter()
        for _ in range(10):
            limiter.acquire()
        m.OPENROUTER_API_KEY = "fake-key"
        try:
            result = ai_parse_dump("test")
            assert result is None
        finally:
            m.OPENROUTER_API_KEY = os.environ.get("BUJO_AI_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
