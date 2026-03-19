"""Tests for bujo.symbols — canonical symbol definitions."""

from bujo.symbols import (
    SYMBOLS,
    SYMBOL_DISPLAY,
    SYMBOL_COLORS,
    LEGACY_UNICODE_TO_ASCII,
    ENTRY_SORT_ORDER,
)


class TestSymbols:
    def test_all_symbols_defined(self):
        expected = {"t", "x", ">", "<", "k", "n", "e", "*"}
        assert set(SYMBOLS.keys()) == expected

    def test_scheduled_symbol(self):
        assert SYMBOLS["<"] == ("Scheduled", "Pulled from future log")
        assert SYMBOL_DISPLAY["<"] == "\u2190"
        assert SYMBOL_COLORS["<"] == "blue"
        assert ENTRY_SORT_ORDER["<"] == 6

    def test_all_displays_defined(self):
        assert set(SYMBOL_DISPLAY.keys()) == set(SYMBOLS.keys())

    def test_all_colors_defined(self):
        assert set(SYMBOL_COLORS.keys()) == set(SYMBOLS.keys())

    def test_legacy_maps_back_to_ascii(self):
        for uni, ascii_sym in LEGACY_UNICODE_TO_ASCII.items():
            assert ascii_sym in SYMBOLS

    def test_sort_order_covers_all(self):
        assert set(ENTRY_SORT_ORDER.keys()) == set(SYMBOLS.keys())

    def test_priority_sorts_first(self):
        assert ENTRY_SORT_ORDER["*"] < ENTRY_SORT_ORDER["t"]

    def test_display_unicode_not_ascii(self):
        # Task display is · (U+00B7), not plain dot
        assert SYMBOL_DISPLAY["t"] == "\u00b7"
