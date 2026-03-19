"""Data models for BuJo entries and logs."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from bujo.symbols import SYMBOLS, SYMBOL_DISPLAY, LEGACY_UNICODE_TO_ASCII


@dataclass
class Entry:
    symbol: str
    display: str
    text: str
    type: str
    raw: str
    source_file: Path
    date: date


@dataclass
class DayLog:
    date: date
    path: Path
    entries: list[Entry] = field(default_factory=list)

    @property
    def done(self) -> list[Entry]:
        return [e for e in self.entries if e.symbol == "x"]

    @property
    def pending(self) -> list[Entry]:
        return [e for e in self.entries if e.symbol == "t"]

    @property
    def priorities(self) -> list[Entry]:
        return [e for e in self.entries if e.symbol == "*"]

    @property
    def killed(self) -> list[Entry]:
        return [e for e in self.entries if e.symbol == "k"]

    @property
    def migrated(self) -> list[Entry]:
        return [e for e in self.entries if e.symbol == ">"]

    @property
    def events(self) -> list[Entry]:
        return [e for e in self.entries if e.symbol == "e"]

    @property
    def completion_rate(self) -> float:
        total = len(self.done) + len(self.pending)
        return len(self.done) / total if total > 0 else 0.0


def read_text_safe(path: Path) -> str:
    """Read text file with UTF-8, falling back to cp1252 for legacy files."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")
    except (OSError, PermissionError):
        return ""


def parse_entries(content: str, source_file: Path, file_date: date) -> list[Entry]:
    """Parse log content into a list of Entry objects.

    Handles both new ASCII format (t, x, >, k, n, e, *)
    and legacy Unicode format (·, ×, >, ~, –, ○, ★).
    """
    entries: list[Entry] = []

    # Unicode display symbols used as legacy prefixes (no space after)
    unicode_prefixes = {
        "\u00b7": "t",  # · -> t
        "\u00d7": "x",  # × -> x
        "~": "k",  # ~ -> k
        "\u2013": "n",  # – -> n
        "\u25cb": "e",  # ○ -> e
        "\u2605": "*",  # ★ -> *
    }

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        sym = None
        text = ""

        # Try ASCII symbol + space (new format): "t buy milk"
        for ascii_sym in SYMBOLS:
            if stripped.startswith(ascii_sym + " "):
                sym = ascii_sym
                text = stripped[len(ascii_sym) + 1 :].strip()
                break

        # Try Unicode symbol (legacy format): "· buy milk" or "·buy milk"
        if sym is None:
            for uni_char, uni_sym in unicode_prefixes.items():
                if stripped.startswith(uni_char):
                    sym = uni_sym
                    after = stripped[len(uni_char) :].strip()
                    text = after if after else ""
                    break

        if sym is not None:
            name, _ = SYMBOLS.get(sym, ("Unknown", ""))
            display = SYMBOL_DISPLAY.get(sym, sym)
            entries.append(
                Entry(
                    symbol=sym,
                    display=display,
                    text=text,
                    type=name,
                    raw=stripped,
                    source_file=source_file,
                    date=file_date,
                )
            )

    return entries


class LogReader:
    """Loads DayLog objects from the vault."""

    def __init__(self, vault: Path):
        self.vault = vault
        self.daily = vault / "daily"

    def load_day(self, d: date) -> DayLog:
        """Load a single day. Returns empty DayLog if file not found."""
        path = self.daily / f"{d.isoformat()}.md"
        if not path.exists():
            return DayLog(date=d, path=path, entries=[])
        content = read_text_safe(path)
        entries = parse_entries(content, path, d)
        return DayLog(date=d, path=path, entries=entries)

    def load_range(self, days: int = 30) -> list[DayLog]:
        """Load last N days. Skips missing files. Sorted oldest first."""
        from datetime import timedelta

        today = date.today()
        logs: list[DayLog] = []
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            logs.append(self.load_day(d))
        return logs

    def load_all(self) -> list[DayLog]:
        """Load every daily file in the vault. Sorted oldest first."""
        if not self.daily.exists():
            return []
        files = sorted(self.daily.glob("*.md"))
        logs: list[DayLog] = []
        for f in files:
            try:
                d = date.fromisoformat(f.stem)
                content = read_text_safe(f)
                entries = parse_entries(content, f, d)
                logs.append(DayLog(date=d, path=f, entries=entries))
            except ValueError:
                continue
        return logs
