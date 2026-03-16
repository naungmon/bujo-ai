"""AI-powered dump capture for BuJo."""

import json
import os
import sys
from pathlib import Path
from datetime import date

import requests

from bujo.app import today_path, today_log, append_entry, SYMBOL_DISPLAY, SYMBOLS


class AIParseError(Exception):
    """Raised when AI response cannot be parsed."""

    def __init__(self, raw_response: str) -> None:
        self.raw_response = raw_response
        super().__init__(f"Failed to parse AI response: {raw_response[:200]}")


def get_ai_config() -> tuple[str, str] | None:
    """Read AI configuration from environment variables.

    Key resolution order:
      1. BUJO_AI_KEY (app-specific, takes priority)
      2. OPENROUTER_API_KEY (fallback)

    Model: BUJO_AI_MODEL (default: minimax/minimax-m2.5)

    Returns (api_key, model) or None if no key is set.
    """
    api_key = os.environ.get("BUJO_AI_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None
    model = os.environ.get("BUJO_AI_MODEL", "minimax/minimax-m2.5")
    return (api_key, model)


def show_setup_instructions() -> None:
    """Print OS-appropriate setup instructions for AI configuration."""
    is_windows = sys.platform == "win32"

    windows_block = (
        "Windows (PowerShell):\n"
        '  $env:BUJO_AI_KEY="sk-or-..."\n'
        '  $env:BUJO_AI_MODEL="minimax/minimax-m2.5"   # optional\n'
        "\n"
        "To make permanent on Windows:\n"
        '  [System.Environment]::SetEnvironmentVariable("BUJO_AI_KEY", "sk-or-...", "User")'
    )

    unix_block = (
        "Mac/Linux — add to ~/.zshrc or ~/.bashrc:\n"
        "  export BUJO_AI_KEY=sk-or-...\n"
        "  export BUJO_AI_MODEL=minimax/minimax-m2.5    # optional"
    )

    if is_windows:
        os_block = windows_block + "\n\n" + unix_block
    else:
        os_block = unix_block + "\n\n" + windows_block

    print(
        f"bujo-ai requires an OpenRouter API key.\n\n"
        f"If you already have OPENROUTER_API_KEY set, you're good — "
        f"bujo-ai will use it.\n"
        f"Otherwise set BUJO_AI_KEY specifically for this app.\n\n"
        f"{os_block}\n\n"
        f"Key resolution order:\n"
        f"  1. BUJO_AI_KEY (app-specific, takes priority)\n"
        f"  2. OPENROUTER_API_KEY (fallback, used if BUJO_AI_KEY not set)\n\n"
        f"Get a key at: openrouter.ai/keys\n"
        f"Default model: minimax/minimax-m2.5"
    )


SYSTEM_PROMPT = (
    "You are a BuJo (Bullet Journal) entry parser.\n"
    "Parse the user's text into structured journal entries.\n"
    "\n"
    "Symbols:\n"
    "  t  = task (something to do)\n"
    "  x  = done (already completed)\n"
    "  n  = note (thought, feeling, observation)\n"
    "  e  = event (scheduled or happened)\n"
    "  *  = priority (urgent or important)\n"
    "  k  = killed (consciously dropped)\n"
    "  >  = migrated (carrying forward)\n"
    "\n"
    "Rules:\n"
    "- Things to do → t\n"
    "- Things already done → x\n"
    "- Feelings, thoughts, observations → n\n"
    "- Scheduled things with a time or date → e\n"
    "- Anything marked urgent, important, or critical → *\n"
    "- Keep the text concise, remove filler words\n"
    "- Split compound sentences into separate entries\n"
    "- Preserve names, times, and specific details\n"
    "\n"
    "Return ONLY a valid JSON array. No explanation. No markdown fences. No preamble.\n"
    'Example: [{"symbol":"t","text":"call jackson about contract"},'
    '{"symbol":"n","text":"feeling scattered today"}]'
)

VALID_SYMBOLS = {"t", "x", "n", "e", "*", "k", ">"}


def parse_dump(text: str, api_key: str, model: str) -> list[tuple[str, str]]:
    """Call OpenRouter API to parse free-form text into BuJo entries.

    Returns list of (symbol, text) tuples.
    Raises AIParseError if response cannot be parsed.
    """
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        },
        timeout=30,
    )

    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]

    # Strip markdown fences if present
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        stripped = "\n".join(lines)

    try:
        entries = json.loads(stripped)
    except json.JSONDecodeError:
        raise AIParseError(content)

    if not isinstance(entries, list):
        raise AIParseError(content)

    result: list[tuple[str, str]] = []
    for item in entries:
        sym = item.get("symbol", "")
        txt = item.get("text", "")
        if sym and txt and sym in VALID_SYMBOLS:
            result.append((sym, txt))

    if not result:
        raise AIParseError(content)

    return result


def save_dump_and_parse(
    text: str, vault: Path
) -> tuple[bool, list[tuple[str, str]], str]:
    """Save raw dump text and parse with AI.

    Returns (success, entries, error_message).
    Raw text is saved to file BEFORE any API call — nothing is ever lost.
    """
    import bujo.app as app_mod

    # 1. Save raw paragraph first — always
    p = app_mod.today_path()
    if not p.exists():
        app_mod.today_log()
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"\n## dump\n{text}\n## /dump\n")

    # 2. Get AI config
    config = get_ai_config()
    if config is None:
        return (False, [], "no_key")

    api_key, model = config

    # 3. Call AI parser
    try:
        entries = parse_dump(text, api_key, model)
    except AIParseError as e:
        return (False, [], f"parse_failed: {e.raw_response[:200]}")
    except requests.RequestException as e:
        return (False, [], f"network_error: {str(e)}")

    # 4. Append structured entries
    for sym, entry_text in entries:
        append_entry(sym, entry_text)

    return (True, entries, "")
