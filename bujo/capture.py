"""NLP-lite capture and templates for BuJo."""

from pathlib import Path

from bujo.models import SYMBOL_DISPLAY, SYMBOLS


def parse_quick_input(text: str) -> tuple[str, str]:
    """Parse input text and return (symbol, cleaned_text).

    Rules applied in order:
    1. starts with 'note:' or 'n:'        -> ('n', rest)
    2. starts with 'event:' or 'e:'       -> ('e', rest)
    3. ends with '!' or starts with '!'   -> ('*', stripped text)
    4. contains ' important' or ' urgent' -> ('*', text without keyword)
    5. done: starts with 'done'           -> ('x', rest)
    6. default                            -> ('t', text)
    """
    text = text.strip()
    if not text:
        return ("t", "")

    lower = text.lower()

    # Rule 1: note prefix
    if lower.startswith("note:") or lower.startswith("n:"):
        prefix_len = 5 if lower.startswith("note:") else 2
        return ("n", text[prefix_len:].strip())

    # Rule 2: event prefix
    if lower.startswith("event:") or lower.startswith("e:"):
        prefix_len = 6 if lower.startswith("event:") else 2
        return ("e", text[prefix_len:].strip())

    # Rule 3: done prefix
    if lower.startswith("done:") or lower.startswith("done "):
        prefix_len = 5 if lower.startswith("done:") else 5
        return ("x", text[prefix_len:].strip())

    # Rule 4: exclamation mark
    if text.endswith("!") or text.startswith("!"):
        cleaned = text.strip("!").strip()
        return ("*", cleaned)

    # Rule 5: important/urgent keywords
    if " important" in lower or " urgent" in lower:
        cleaned = text
        for kw in [" important", " urgent", " Important", " Urgent"]:
            cleaned = cleaned.replace(kw, "")
        return ("*", cleaned.strip())

    # Rule 6: default
    return ("t", text)


def detect_type(text: str) -> tuple[str, str]:
    """Detect symbol type without modifying text. Returns (symbol, type_name)."""
    symbol, _ = parse_quick_input(text)
    name, _ = SYMBOLS.get(symbol, ("Task", ""))
    return symbol, name


def ensure_templates(vault: Path) -> None:
    """Create templates directory with default templates if not exists."""
    templates_dir = vault / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    morning = templates_dir / "morning.md"
    if not morning.exists():
        morning.write_text(
            "* What is the one thing that would make today complete?\n"
            "n How am I feeling right now?\n"
            "t Review yesterday's pending tasks\n",
            encoding="utf-8",
        )

    evening = templates_dir / "evening.md"
    if not evening.exists():
        evening.write_text(
            "n What did I actually get done today?\n"
            "n What do I want to remember from today?\n"
            "t What needs to carry forward to tomorrow?\n",
            encoding="utf-8",
        )

    weekly = templates_dir / "weekly.md"
    if not weekly.exists():
        weekly.write_text(
            "n What was this week's win?\n"
            "n What kept getting avoided?\n"
            "* What is the priority for next week?\n",
            encoding="utf-8",
        )


def apply_template(name: str, vault: Path) -> list[tuple[str, str]]:
    """Load vault/templates/{name}.md and parse each line as (symbol, text).
    Returns list of (symbol, text) tuples. Skips blanks and comments."""
    ensure_templates(vault)
    template_path = vault / "templates" / f"{name}.md"
    if not template_path.exists():
        return []

    entries: list[tuple[str, str]] = []

    for line in template_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Check ASCII symbol prefixes
        for sym in SYMBOLS:
            if stripped.startswith(sym + " "):
                text = stripped[len(sym) + 1 :].strip()
                entries.append((sym, text))
                break
        else:
            # Check legacy Unicode symbols
            for display, sym in SYMBOL_DISPLAY.items():
                if stripped.startswith(display + " "):
                    text = stripped[len(display) + 1 :].strip()
                    entries.append((sym, text))
                    break

    return entries
