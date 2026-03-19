"""Tests for search across vault entries."""

from datetime import date
from pathlib import Path

import pytest

from bujo.views.search import search_vault


class TestSearchVault:
    def _create_vault(self, tmp_path, files: dict[str, str]) -> Path:
        daily = tmp_path / "daily"
        daily.mkdir(parents=True)
        for name, content in files.items():
            (daily / name).write_text(content, encoding="utf-8")
        return tmp_path

    def test_finds_matching_entries(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-17.md": "# Wednesday, March 17 2026\n\nt call Jackson\nn feeling good",
            "2026-03-16.md": "# Tuesday, March 16 2026\n\nt buy milk\nt call Jackson again",
        })
        results = search_vault("jackson", vault)
        assert len(results) == 2
        assert all("jackson" in r["text"].lower() for r in results)

    def test_case_insensitive(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-17.md": "# Wednesday, March 17 2026\n\nt Call JACKSON",
        })
        results = search_vault("jackson", vault)
        assert len(results) == 1

    def test_no_results(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-17.md": "# Wednesday, March 17 2026\n\nt buy milk",
        })
        results = search_vault("nonexistent", vault)
        assert results == []

    def test_results_include_date(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-17.md": "# Wednesday, March 17 2026\n\nt buy milk",
        })
        results = search_vault("milk", vault)
        assert results[0]["date"] == "2026-03-17"

    def test_results_sorted_newest_first(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-15.md": "# Saturday, March 15 2026\n\nt milk",
            "2026-03-17.md": "# Monday, March 17 2026\n\nt milk",
            "2026-03-16.md": "# Sunday, March 16 2026\n\nt milk",
        })
        results = search_vault("milk", vault)
        dates = [r["date"] for r in results]
        assert dates == ["2026-03-17", "2026-03-16", "2026-03-15"]

    def test_empty_query_returns_empty(self, tmp_path):
        vault = self._create_vault(tmp_path, {
            "2026-03-17.md": "# Wednesday, March 17 2026\n\nt buy milk",
        })
        results = search_vault("", vault)
        assert results == []
