"""Tests for bujo.vault — vault file I/O operations."""

import os
from datetime import date
from pathlib import Path

import pytest

from bujo.vault import (
    ensure_vault,
    today_path,
    today_log,
    save_today,
    append_entry,
    read_text_safe,
    get_monthly_path,
    get_future_path,
    has_any_daily_files,
    parse_future_log,
    get_future_items_for_month,
    append_future_entry,
    mark_future_entry_done,
)


class TestEnsureVault:
    def test_creates_directories(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path / "test-vault"))
        # Re-import to pick up new env
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        bujo.vault.ensure_vault()
        assert (tmp_path / "test-vault" / "daily").is_dir()
        assert (tmp_path / "test-vault" / "monthly").is_dir()
        assert (tmp_path / "test-vault" / "future").is_dir()


class TestAppendEntry:
    def test_creates_file_and_appends(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        bujo.vault.ensure_vault()
        bujo.vault.append_entry("t", "buy milk")
        p = bujo.vault.today_path()
        content = p.read_text(encoding="utf-8")
        assert "t buy milk" in content

    def test_appends_to_existing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        bujo.vault.ensure_vault()
        bujo.vault.append_entry("t", "first")
        bujo.vault.append_entry("n", "second")
        content = bujo.vault.today_path().read_text(encoding="utf-8")
        assert "t first" in content
        assert "n second" in content


class TestReadTextSafe:
    def test_utf8(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("hello", encoding="utf-8")
        assert read_text_safe(p) == "hello"

    def test_missing_file(self, tmp_path):
        assert read_text_safe(tmp_path / "nope.md") == ""


class TestFutureLogHelpers:
    def test_parse_future_log_groups_by_month(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        future_dir = tmp_path / "future"
        future_dir.mkdir(exist_ok=True)
        future_file = future_dir / "future.md"
        future_file.write_text(
            "# Future Log\n\n"
            "## June 2026\n"
            "> call dentist\n"
            "> renew passport\n\n"
            "## August 2026\n"
            "> Sarah's birthday dinner\n",
            encoding="utf-8",
        )
        result = bujo.vault.parse_future_log()
        assert "June 2026" in result
        assert "August 2026" in result
        assert result["June 2026"][0] == "> call dentist"
        assert result["June 2026"][1] == "> renew passport"
        assert result["August 2026"][0] == "> Sarah's birthday dinner"

    def test_parse_future_log_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        future_dir = tmp_path / "future"
        future_dir.mkdir(exist_ok=True)
        (future_dir / "future.md").write_text("", encoding="utf-8")
        result = bujo.vault.parse_future_log()
        assert result == {}

    def test_parse_future_log_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        result = bujo.vault.parse_future_log()
        assert result == {}

    def test_get_future_items_for_month(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        future_dir = tmp_path / "future"
        future_dir.mkdir(exist_ok=True)
        (future_dir / "future.md").write_text(
            "# Future Log\n\n"
            "## June 2026\n"
            "> call dentist\n"
            "> renew passport\n\n"
            "## July 2026\n"
            "> summer trip\n",
            encoding="utf-8",
        )
        result = bujo.vault.get_future_items_for_month(2026, 6)
        assert result == ["call dentist", "renew passport"]

    def test_get_future_items_for_month_none(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        future_dir = tmp_path / "future"
        future_dir.mkdir(exist_ok=True)
        (future_dir / "future.md").write_text("# Future Log\n\n", encoding="utf-8")
        result = bujo.vault.get_future_items_for_month(2026, 6)
        assert result == []

    def test_append_future_entry_new_header(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        future_dir = tmp_path / "future"
        future_dir.mkdir(exist_ok=True)
        (future_dir / "future.md").write_text("# Future Log\n\n", encoding="utf-8")
        bujo.vault.append_future_entry("call dentist", "June 2026")
        content = (future_dir / "future.md").read_text(encoding="utf-8")
        assert "## June 2026" in content
        assert "> call dentist" in content

    def test_append_future_entry_existing_header(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        future_dir = tmp_path / "future"
        future_dir.mkdir(exist_ok=True)
        (future_dir / "future.md").write_text(
            "# Future Log\n\n## June 2026\n> existing task\n", encoding="utf-8"
        )
        bujo.vault.append_future_entry("new task", "June 2026")
        content = (future_dir / "future.md").read_text(encoding="utf-8")
        assert content.count("> new task") == 1
        assert "> existing task" in content

    def test_mark_future_entry_done(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BUJO_VAULT", str(tmp_path))
        import importlib
        import bujo.vault
        importlib.reload(bujo.vault)
        future_dir = tmp_path / "future"
        future_dir.mkdir(exist_ok=True)
        (future_dir / "future.md").write_text(
            "# Future Log\n\n## June 2026\n> call dentist\n> renew passport\n",
            encoding="utf-8",
        )
        bujo.vault.mark_future_entry_done("call dentist")
        content = (future_dir / "future.md").read_text(encoding="utf-8")
        assert "> call dentist" not in content
        assert "x call dentist" in content
        assert "> renew passport" in content
