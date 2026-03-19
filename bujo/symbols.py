"""Canonical symbol definitions for BuJo.

Single source of truth. All other modules import from here.
"""

# ASCII symbols stored in markdown files
SYMBOLS = {
    "t": ("Task", "Something to do"),
    "x": ("Done", "Completed"),
    ">": ("Migrated", "Moved forward"),
    "<": ("Scheduled", "Pulled from future log"),
    "k": ("Killed", "Consciously dropped"),
    "n": ("Note", "Thought or observation"),
    "e": ("Event", "Happened or scheduled"),
    "*": ("Priority", "This one matters today"),
}

# TUI display symbols (Unicode render)
SYMBOL_DISPLAY = {
    "t": "\u00b7",  # ·
    "x": "\u00d7",  # ×
    ">": ">",
    "<": "\u2190",  # ←
    "k": "~",
    "n": "\u2013",  # –
    "e": "\u25cb",  # ○
    "*": "\u2605",  # ★
}

# TUI colors per symbol
SYMBOL_COLORS = {
    "t": "cyan",
    "x": "green",
    ">": "blue",
    "<": "blue",
    "k": "dim",
    "n": "white",
    "e": "magenta",
    "*": "red",
}

# Legacy Unicode -> ASCII mapping for backward compatibility
LEGACY_UNICODE_TO_ASCII = {
    "\u00b7": "t",
    "\u00d7": "x",
    "~": "k",
    "\u2013": "n",
    "\u25cb": "e",
    "\u2605": "*",
}

# Sort order for entry display (priority first, done/migrated last)
ENTRY_SORT_ORDER = {"*": 0, "t": 1, "e": 2, "n": 3, "k": 4, "x": 5, ">": 6, "<": 6}
