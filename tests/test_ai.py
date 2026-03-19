"""Tests for bujo.ai — AI dump capture (all API calls mocked)."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

from bujo.ai import (
    parse_dump,
    save_dump_and_parse,
    AIParseError,
    get_ai_config,
    show_setup_instructions,
    SYSTEM_PROMPT,
    INJECTION_GUARD,
    VALID_SYMBOLS,
)


# ---------------------------------------------------------------------------
# get_ai_config
# ---------------------------------------------------------------------------


class TestGetAIConfig:
    def test_missing_key(self, monkeypatch):
        monkeypatch.delenv("BUJO_AI_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        assert get_ai_config() is None

    def test_with_bujo_key(self, monkeypatch):
        monkeypatch.setenv("BUJO_AI_KEY", "sk-or-test")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        result = get_ai_config()
        assert result == ("sk-or-test", "minimax/minimax-m2.7")

    def test_with_openrouter_fallback(self, monkeypatch):
        monkeypatch.delenv("BUJO_AI_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-fallback")
        result = get_ai_config()
        assert result == ("sk-or-fallback", "minimax/minimax-m2.7")

    def test_bujo_key_takes_priority(self, monkeypatch):
        monkeypatch.setenv("BUJO_AI_KEY", "sk-or-primary")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-fallback")
        result = get_ai_config()
        assert result[0] == "sk-or-primary"

    def test_custom_model(self, monkeypatch):
        monkeypatch.setenv("BUJO_AI_KEY", "sk-or-test")
        monkeypatch.setenv("BUJO_AI_MODEL", "anthropic/claude-3")
        result = get_ai_config()
        assert result == ("sk-or-test", "anthropic/claude-3")


# ---------------------------------------------------------------------------
# show_setup_instructions
# ---------------------------------------------------------------------------


class TestShowSetupInstructions:
    def test_output_contains_key_info(self, capsys):
        show_setup_instructions()
        captured = capsys.readouterr()
        assert "OpenRouter" in captured.out
        assert "BUJO_AI_KEY" in captured.out
        assert "openrouter.ai/keys" in captured.out

    def test_windows_instructions_first(self, capsys):
        with patch("bujo.ai.sys.platform", "win32"):
            show_setup_instructions()
            captured = capsys.readouterr()
            windows_pos = captured.out.find("Windows")
            unix_pos = captured.out.find("Mac/Linux")
            assert windows_pos < unix_pos

    def test_unix_instructions_first(self, capsys):
        with patch("bujo.ai.sys.platform", "darwin"):
            show_setup_instructions()
            captured = capsys.readouterr()
            unix_pos = captured.out.find("Mac/Linux")
            windows_pos = captured.out.find("Windows")
            assert unix_pos < windows_pos


# ---------------------------------------------------------------------------
# parse_dump
# ---------------------------------------------------------------------------


class TestParseDump:
    def _mock_response(self, content: str) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": content}}]}
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    @patch("bujo.ai.requests.post")
    def test_success(self, mock_post):
        data = [
            {"symbol": "t", "text": "call jackson"},
            {"symbol": "n", "text": "feeling scattered"},
        ]
        mock_post.return_value = self._mock_response(json.dumps(data))
        result = parse_dump("some dump text", "sk-test", "model")
        assert result == [("t", "call jackson"), ("n", "feeling scattered")]

    @patch("bujo.ai.requests.post")
    def test_strips_markdown_fences(self, mock_post):
        data = [
            {"symbol": "t", "text": "call jackson"},
            {"symbol": "n", "text": "feeling scattered"},
        ]
        mock_post.return_value = self._mock_response(
            f"```json\n{json.dumps(data)}\n```"
        )
        result = parse_dump("dump", "sk-test", "model")
        assert result == [("t", "call jackson"), ("n", "feeling scattered")]

    @patch("bujo.ai.requests.post")
    def test_strips_markdown_fences_no_language(self, mock_post):
        data = [{"symbol": "t", "text": "call jackson"}]
        mock_post.return_value = self._mock_response(f"```\n{json.dumps(data)}\n```")
        result = parse_dump("dump", "sk-test", "model")
        assert result == [("t", "call jackson")]

    @patch("bujo.ai.requests.post")
    def test_invalid_json_raises(self, mock_post):
        mock_post.return_value = self._mock_response("not json at all")
        with pytest.raises(AIParseError) as exc_info:
            parse_dump("dump", "sk-test", "model")
        assert "not json at all" in exc_info.value.raw_response

    @patch("bujo.ai.requests.post")
    def test_empty_list_raises(self, mock_post):
        mock_post.return_value = self._mock_response("[]")
        with pytest.raises(AIParseError):
            parse_dump("dump", "sk-test", "model")

    @patch("bujo.ai.requests.post")
    def test_missing_fields_skipped(self, mock_post):
        data = [
            {"symbol": "t", "text": "valid entry"},
            {"text": "no symbol"},
            {"symbol": "t"},
            {"symbol": "INVALID", "text": "bad symbol"},
        ]
        mock_post.return_value = self._mock_response(json.dumps(data))
        result = parse_dump("dump", "sk-test", "model")
        assert result == [("t", "valid entry")]

    @patch("bujo.ai.requests.post")
    def test_non_list_response_raises(self, mock_post):
        mock_post.return_value = self._mock_response('{"key": "value"}')
        with pytest.raises(AIParseError):
            parse_dump("dump", "sk-test", "model")

    @patch("bujo.ai.requests.post")
    def test_network_error_propagates(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("no connection")
        with pytest.raises(requests.ConnectionError):
            parse_dump("dump", "sk-test", "model")

    @patch("bujo.ai.requests.post")
    def test_timeout_propagates(self, mock_post):
        mock_post.side_effect = requests.Timeout("timeout")
        with pytest.raises(requests.Timeout):
            parse_dump("dump", "sk-test", "model")

    @patch("bujo.ai.requests.post")
    def test_correct_api_call(self, mock_post):
        mock_post.return_value = self._mock_response('[{"symbol":"t","text":"hi"}]')
        parse_dump("my dump text", "sk-test-key", "my-model")
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["headers"]["Authorization"] == "Bearer sk-test-key"
        assert call_kwargs[1]["json"]["model"] == "my-model"
        assert call_kwargs[1]["json"]["messages"][1]["content"] == INJECTION_GUARD + "my dump text"
        assert call_kwargs[1]["json"]["messages"][0]["content"] == SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# save_dump_and_parse
# ---------------------------------------------------------------------------


class TestSaveDumpAndParse:
    def test_saves_raw_first(self, tmp_path):
        vault = tmp_path
        daily = vault / "daily"
        daily.mkdir()

        with patch("bujo.ai.today_path") as mock_today_path:
            today_file = daily / "2026-03-16.md"
            today_file.write_text("# March 16\n\n", encoding="utf-8")
            mock_today_path.return_value = today_file

            with patch("bujo.ai.get_ai_config", return_value=None):
                success, entries, err = save_dump_and_parse("my raw dump text", vault)

        content = today_file.read_text(encoding="utf-8")
        assert "## dump" in content
        assert "my raw dump text" in content
        assert "## /dump" in content

    def test_no_key(self, tmp_path):
        vault = tmp_path
        daily = vault / "daily"
        daily.mkdir()

        with patch("bujo.ai.today_path") as mock_today_path:
            today_file = daily / "2026-03-16.md"
            today_file.write_text("# March 16\n\n", encoding="utf-8")
            mock_today_path.return_value = today_file

            with patch("bujo.ai.get_ai_config", return_value=None):
                success, entries, err = save_dump_and_parse("test", vault)

        assert success is False
        assert entries == []
        assert err == "no_key"

    @patch("bujo.ai.requests.post")
    def test_network_error(self, mock_post, tmp_path):
        vault = tmp_path
        daily = vault / "daily"
        daily.mkdir()
        mock_post.side_effect = requests.ConnectionError("no connection")

        with patch("bujo.ai.today_path") as mock_today_path:
            today_file = daily / "2026-03-16.md"
            today_file.write_text("# March 16\n\n", encoding="utf-8")
            mock_today_path.return_value = today_file

            with patch("bujo.ai.get_ai_config", return_value=("sk-test", "model")):
                success, entries, err = save_dump_and_parse("test", vault)

        assert success is False
        assert entries == []
        assert "network_error" in err

    @patch("bujo.ai.requests.post")
    def test_parse_failed(self, mock_post, tmp_path):
        vault = tmp_path
        daily = vault / "daily"
        daily.mkdir()
        mock_post.return_value = MagicMock(
            json=MagicMock(
                return_value={"choices": [{"message": {"content": "not json"}}]}
            ),
            raise_for_status=MagicMock(),
        )

        with patch("bujo.ai.today_path") as mock_today_path:
            today_file = daily / "2026-03-16.md"
            today_file.write_text("# March 16\n\n", encoding="utf-8")
            mock_today_path.return_value = today_file

            with patch("bujo.ai.get_ai_config", return_value=("sk-test", "model")):
                success, entries, err = save_dump_and_parse("test", vault)

        assert success is False
        assert entries == []
        assert "parse_failed" in err

    @patch("bujo.ai.requests.post")
    def test_appends_entries_on_success(self, mock_post, tmp_path):
        vault = tmp_path
        daily = vault / "daily"
        daily.mkdir()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '[{"symbol":"t","text":"call jackson"},{"symbol":"n","text":"feeling scattered"}]'
                    }
                }
            ]
        }
        mock_resp.raise_for_status.return_value = None
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        today_file = daily / "2026-03-16.md"
        today_file.write_text("# March 16\n\n", encoding="utf-8")

        with patch("bujo.ai.today_path", return_value=today_file), \
             patch("bujo.vault.today_path", return_value=today_file), \
             patch("bujo.ai.get_ai_config", return_value=("sk-test", "model")):
            success, entries, err = save_dump_and_parse(
                "need to call jackson, feeling scattered", vault
            )

        assert success is True
        assert len(entries) == 2
        assert entries[0] == ("t", "call jackson")
        assert entries[1] == ("n", "feeling scattered")

        content = today_file.read_text(encoding="utf-8")
        assert "## dump" in content
        assert "t call jackson" in content
        assert "n feeling scattered" in content


# ---------------------------------------------------------------------------
# AIParseError
# ---------------------------------------------------------------------------


class TestValidSymbols:
    def test_includes_scheduled(self):
        """VALID_SYMBOLS must include < (scheduled) symbol."""
        assert "<" in VALID_SYMBOLS

    def test_includes_all_bujo_symbols(self):
        """VALID_SYMBOLS must include all 8 BuJo symbols."""
        from bujo.symbols import SYMBOLS
        for sym in SYMBOLS:
            assert sym in VALID_SYMBOLS, f"Missing symbol: {sym}"


class TestAIParseError:
    def test_stores_raw_response(self):
        err = AIParseError("garbled response here")
        assert err.raw_response == "garbled response here"

    def test_message_includes_raw(self):
        err = AIParseError("garbled response here")
        assert "garbled response here" in str(err)


# ---------------------------------------------------------------------------
# Dump block invisible to parse_entries
# ---------------------------------------------------------------------------


class TestDumpBlockInvisibility:
    def test_dump_block_not_parsed(self):
        from bujo.models import parse_entries
        from datetime import date as d

        content = (
            "# March 16, 2026\n\n"
            "t buy milk\n"
            "n feeling good\n"
            "## dump\n"
            "raw paragraph here with lots of text\n"
            "## /dump\n"
            "t call jackson\n"
            "n feeling scattered\n"
        )
        entries = parse_entries(content, Path("test.md"), d(2026, 3, 16))

        assert len(entries) == 4
        assert entries[0].text == "buy milk"
        assert entries[1].text == "feeling good"
        assert entries[2].text == "call jackson"
        assert entries[3].text == "feeling scattered"
