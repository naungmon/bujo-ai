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
