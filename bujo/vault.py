"""Vault file I/O for BuJo.

All filesystem operations live here. This is the module a future
GUI would swap out for its own storage backend.
"""

import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

_bujo_vault_env = os.environ.get("BUJO_VAULT", "")
if _bujo_vault_env:
    _vault_path = Path(_bujo_vault_env)
    if ".." in _vault_path.parts:
        raise ValueError(
            f"BUJO_VAULT may not contain '..' path components: {_vault_path}"
        )
    VAULT = _vault_path.resolve()
else:
    VAULT = Path.home() / "bujo-vault"
DAILY = VAULT / "daily"
FUTURE = VAULT / "future"
MONTHLY = VAULT / "monthly"
REFLECTIONS = VAULT / "reflections"
FIRST_RUN_FLAG = Path.home() / ".bujo-first-run-done"


def open_in_editor(path: Path | str) -> None:
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        editor = "notepad" if sys.platform == "win32" else "nano"
    try:
        subprocess.run([editor, str(path)], check=False)
    except FileNotFoundError:
        pass


def ensure_vault() -> None:
    for d in [DAILY, FUTURE, MONTHLY, REFLECTIONS]:
        d.mkdir(parents=True, exist_ok=True)


def today_path() -> Path:
    return DAILY / f"{date.today().isoformat()}.md"


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")
    except (OSError, PermissionError):
        return ""


def today_log() -> str:
    p = today_path()
    if not p.exists():
        header = f"# {date.today().strftime('%A, %B %d %Y')}\n\n"
        p.write_text(header, encoding="utf-8")
    return read_text_safe(p)


def save_today(content: str) -> None:
    today_path().write_text(content, encoding="utf-8")


def append_entry(symbol: str, text: str) -> None:
    p = today_path()
    if not p.exists():
        today_log()
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"{symbol} {text}\n")


def get_monthly_path() -> Path:
    return MONTHLY / f"{date.today().strftime('%Y-%m')}.md"


def get_future_path() -> Path:
    return FUTURE / "future.md"


def has_any_daily_files() -> bool:
    if not DAILY.exists():
        return False
    return any(DAILY.glob("*.md"))


def load_user_context() -> str:
    """Load ~/bujo-vault/context/me.md if it exists. Returns empty string if not."""
    path = VAULT / "context" / "me.md"
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, FileNotFoundError):
        return ""


def load_eval_history() -> str:
    """Load ~/bujo-vault/context/evals.md if it exists. Returns empty string if not."""
    path = VAULT / "context" / "evals.md"
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, FileNotFoundError):
        return ""


def append_eval_entry(month_label: str, eval_text: str) -> None:
    """Append a monthly eval summary to ~/bujo-vault/context/evals.md."""
    path = VAULT / "context" / "evals.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    try:
        existing = path.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        existing = "# Eval History\n\nMonthly pattern summaries, accumulated over time.\n\n"
    entry = f"\n## {month_label}\n\n{eval_text.strip()}\n"
    path.write_text(existing + entry, encoding="utf-8")


def update_me_section(section_header: str, new_content: str) -> None:
    """Replace the content of a named section in me.md with new_content.
    Section is identified by ## header. Does nothing if section not found."""
    import re as _re
    path = VAULT / "context" / "me.md"
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return

    pattern = rf"(## {_re.escape(section_header)}\n)(.*?)(?=\n## |\Z)"
    replacement = rf"\g<1>{new_content.strip()}\n"
    new_content_full = _re.sub(pattern, replacement, content, flags=_re.DOTALL)
    path.write_text(new_content_full, encoding="utf-8")


def get_all_logs_summary() -> str:
    lines: list[str] = []
    daily_files = sorted(DAILY.glob("*.md"), reverse=True)[:7]
    for f in daily_files:
        lines.append(f"\n## {f.stem}")
        try:
            lines.append(read_text_safe(f).strip())
        except (OSError, PermissionError):
            lines.append("_(could not read file)_")
    future = get_future_path()
    if future.exists():
        lines.append("\n## Future Log")
        try:
            lines.append(read_text_safe(future).strip())
        except (OSError, PermissionError):
            lines.append("_(could not read file)_")
    monthly = get_monthly_path()
    if monthly.exists():
        lines.append(f"\n## Monthly ({date.today().strftime('%B %Y')})")
        try:
            lines.append(read_text_safe(monthly).strip())
        except (OSError, PermissionError):
            lines.append("_(could not read file)_")
    return "\n".join(lines)


def load_yesterday_pending() -> list[dict]:
    """Load pending 't' tasks from yesterday's log.

    Returns oldest-first list of dicts with keys:
    symbol, display, text, type, raw, source_file, source_date (date object).
    """
    from bujo.models import parse_entries

    yesterday = date.today() - timedelta(days=1)
    path = DAILY / f"{yesterday.isoformat()}.md"
    if not path.exists():
        return []
    content = read_text_safe(path)
    if not content.strip():
        return []
    entries = parse_entries(content, path, yesterday)
    pending = [e for e in entries if e.symbol == "t"]
    pending.sort(key=lambda e: e.raw or "")
    return [
        {
            "symbol": e.symbol,
            "display": e.display,
            "text": e.text,
            "type": e.type,
            "raw": e.raw,
            "source_file": e.source_file,
            "source_date": yesterday,
        }
        for e in pending
    ]
