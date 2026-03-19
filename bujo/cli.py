#!/usr/bin/env python3
"""BuJo CLI entrypoint.

Usage:
    bujo                      Launch the TUI
    bujo add t text           Add a task
    bujo add n text           Add a note
    bujo add * text           Add a priority
    bujo add e text           Add an event
    bujo add x text           Mark as done
    bujo add k text           Add killed entry
    bujo log                  Print today's log
    bujo summary              Print logs summary (legacy)
    bujo coach                Print structured JSON for AI coaching
    bujo coach --human        Human-readable coaching output
    bujo insights             Print human-readable analytics
    bujo week                 Weekly summary
    bujo capture "text"       NLP-parse and add entry
    bujo template name        Apply template to today's log
    bujo streak               Show current streak
    bujo vault                Print vault path
    bujo tutorial             Step-by-step walkthrough
    bujo help                 Show usage
"""

import io
import sys
import json
import os
from typing import cast


def _reconfigure_stdout() -> None:
    try:
        cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
    except Exception:
        pass


def _print_coach_human(report: dict) -> None:
    """Print coach report in human-readable format."""
    if report.get("empty"):
        print("Not enough data yet.")
        print("Keep logging for a few days and patterns will appear.")
        print("\nTry: bujo template morning")
        return

    momentum = report.get("momentum", "unknown")
    streak = report.get("streak", 0)
    completion = report.get("completion_rate_7d", 0)
    alignment = report.get("priority_alignment_7d", 0)
    nudge = report.get("nudge", "")
    stuck = report.get("stuck_tasks", [])
    themes = report.get("kill_themes", {})
    productive = report.get("most_productive_time", "not enough data")

    print(
        "\u2500\u2500\u2500 BuJo Coach \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
    )
    print(
        f"\n  Momentum: {momentum}  \u2502  Streak: {streak} day{'s' if streak != 1 else ''}  \u2502  Done: {completion:.0%}"
    )
    print(
        f"  Alignment: {alignment:.0%} priority completion  \u2502  Productive: {productive}"
    )

    if stuck:
        print("\n  Stuck tasks (migrated 3+ times):")
        for t in stuck[:3]:
            print(f"  \u00b7 {t['text']}  (moved {t['count']}x)")

    if themes:
        print("\n  Kill pattern:")
        top_themes = list(themes.items())[:3]
        theme_str = ", ".join(f"{k} ({v})" for k, v in top_themes)
        print(f"  Most dropped: {theme_str}")

    print(
        "\n  \u2500\u2500 Today's question \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
    )
    print(f"  {nudge}")
    print("\u2500" * 60)


def _print_dump_entries(entries: list[tuple[str, str]]) -> None:
    """Print parsed dump entries with Unicode symbols."""
    from bujo.app import SYMBOL_DISPLAY, SYMBOLS

    type_map = {
        "t": "task",
        "n": "note",
        "e": "event",
        "*": "priority",
        "x": "done",
        "k": "killed",
        ">": "migrated",
    }
    for sym, text in entries:
        d = SYMBOL_DISPLAY.get(sym, sym)
        label = type_map.get(sym, sym)
        print(f"  {d} {text}")


# ─────────────────────────────────────────────────────────────────────────────
TUTORIAL_TEXT = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  BuJo — 2-Minute Tour
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. THE VAULT
   Your journal lives in ~/bujo-vault/ as plain markdown files.
   Open it in Obsidian, VS Code, or any text editor.
   Every day = one file in daily/. Back it up like any important file.

2. PREFIX SETS THE TYPE
   Start any line with a prefix to set its type:
   ┌────────────────────────────────────────────────────────────────────────┐
   │  t / task      →  task (something to do)                              │
   │  n / note      →  note (thought, observation)                         │
   │  e / event     →  event (scheduled or happened)                       │
   │  * / priority  →  priority (urgent or important)                      │
   │  x / done      →  done                                                │
   │  k / kill      →  killed (consciously dropped)                        │
   │  >             →  migrated (carrying forward)                          │
   │  (no prefix)   →  note                                               │
   └────────────────────────────────────────────────────────────────────────┘
   Examples:  t call jackson       note feeling tired today
              * finish report       done wrote tests
              k that idea           event standup at 9

   Priority shortcut: add ! at the end of any line → becomes priority.
   Examples:  finish this report!    k that meeting!

3. NAVIGATE + UPDATE
   ↑↓  Move between the input bar and your entry list
   Enter  submit (in input) or edit (on an entry)
   x      mark selected entry as done
   k      kill selected entry (drop it consciously)
   >      migrate selected entry (carry it forward)
   Ctrl+Z undo last change

4. AI-POWERED CAPTURE
   The main input is always AI-powered.
   Type freely, in full sentences, however messy.
   Hit Enter and AI sorts it into tasks, notes, events, priorities.
   Your raw text is always saved first — nothing is ever lost.

5. VIEWS
   m  →  Monthly View (your 3-5 monthly priorities)
   f  →  Future View (parked items — not dead, not ready)
   Shift+M  →  Migration Screen (review pending tasks, keep/kill/migrate)
   Shift+R  →  Monthly Review
    Ctrl+B  →  Coach (insights for ADHD brains — best after 5+ entries)
   ?  →  This help screen

6. SEARCH
   /  opens full-text search across all your days.
   Useful for finding patterns, old notes, recurring tasks.

7. CLI COMMANDS
   bujo                   launch TUI
   bujo capture "text"    NLP parse (prefix auto-detected)
   bujo dump              multiline AI-powered capture
   bujo dump --retry      re-parse failed AI blocks
   bujo coach --human     readable coaching insights
   bujo insights          analytics dashboard
   bujo week              weekly summary
   bujo template morning  fill your morning routine

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Run `bujo help` for the full command reference.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""  # noqa: E501
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        if not args:
            from bujo.app import BuJoApp, ensure_vault

            ensure_vault()
            BuJoApp().run()
            return
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "add" and len(args) >= 3:
        from bujo.app import append_entry, ensure_vault, SYMBOL_DISPLAY

        ensure_vault()
        symbol = args[1]
        text = " ".join(args[2:])
        append_entry(symbol, text)
        d = SYMBOL_DISPLAY.get(symbol, symbol)
        _reconfigure_stdout()
        print(f"Added: {d} {text}")

    elif cmd == "log":
        from bujo.app import today_log, ensure_vault

        ensure_vault()
        _reconfigure_stdout()
        print(today_log())

    elif cmd == "summary":
        from bujo.app import get_all_logs_summary, ensure_vault

        ensure_vault()
        _reconfigure_stdout()
        print(get_all_logs_summary())

    elif cmd == "coach":
        from bujo.analytics import InsightsEngine
        from bujo.app import VAULT

        engine = InsightsEngine(VAULT)
        report = engine.full_report()
        _reconfigure_stdout()

        if "--human" in args:
            _print_coach_human(report)
        else:
            print(json.dumps(report, indent=2))

    elif cmd == "week":
        from bujo.analytics import InsightsEngine
        from bujo.app import VAULT

        engine = InsightsEngine(VAULT)
        week = engine.weekly_summary()
        _reconfigure_stdout()

        from datetime import datetime

        is_monday = datetime.now().weekday() == 0
        label = "Weekly Summary" if is_monday else "Weekly Summary (mid-week)"

        print(
            f"\u2500\u2500\u2500 {label} \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
        )
        print(f"  Week:         {week['week_range']}")
        print(f"  Logged:       {week['total_logged']} entries")
        print(f"  Done:         {week['total_done']}")
        print(f"  Killed:       {week['total_killed']}")
        print(f"  Migrated:     {week['total_migrated']}")
        print(
            f"  Streak:       {week['streak']} day{'s' if week['streak'] != 1 else ''}"
        )
        print(f"  Productive:   {week['most_productive_time']}")
        print(f"\n  Insight:      {week['top_insight']}")
        print("\u2500" * 60)

    elif cmd == "insights":
        from bujo.analytics import InsightsEngine
        from bujo.app import VAULT

        _reconfigure_stdout()
        engine = InsightsEngine(VAULT)
        report = engine.full_report()

        if report["empty"]:
            print("Not enough data yet.")
            print("Keep logging for a few days and patterns will appear.")
            print("\nTry: bujo template morning")
            return

        momentum = report["momentum"]
        streak = report["streak"]
        completion = report["completion_rate_7d"]
        alignment = report["priority_alignment_7d"]
        nudge = report["nudge"]

        print(f"Momentum:     {momentum}")
        print(f"Streak:       {streak} day{'s' if streak != 1 else ''}")
        print(f"Completion:   {completion:.0%} this week")
        print(f"Priorities:   {alignment:.0%} aligned")

        stuck = report["stuck_tasks"]
        if stuck:
            print(f"\nStuck tasks:")
            for t in stuck[:3]:
                print(f"  \u00b7 {t['text']}  (migrated {t['count']}x)")

        themes = report["kill_themes"]
        if themes:
            theme_str = "  ".join(f"{k} ({v})" for k, v in list(themes.items())[:3])
            print(f"\nYou tend to drop: {theme_str}")

        print(f"\nNudge: {nudge}")

    elif cmd == "capture" and len(args) >= 2:
        from bujo.capture import parse_quick_input
        from bujo.app import append_entry, ensure_vault, SYMBOL_DISPLAY

        ensure_vault()
        text = " ".join(args[1:])
        symbol, cleaned = parse_quick_input(text)
        append_entry(symbol, cleaned)
        d = SYMBOL_DISPLAY.get(symbol, symbol)
        _reconfigure_stdout()
        print(f"Added: {d} {cleaned}")

    elif cmd == "template" and len(args) >= 2:
        from bujo.capture import apply_template
        from bujo.app import append_entry, ensure_vault, VAULT

        ensure_vault()
        template_name = args[1]
        entries = apply_template(template_name, VAULT)

        if not entries:
            _reconfigure_stdout()
            print(f"Template '{template_name}' not found or empty.")
            print("Available: morning, evening, weekly")
            return

        for symbol, text in entries:
            append_entry(symbol, text)

        _reconfigure_stdout()
        print(f"Applied template '{template_name}' ({len(entries)} entries)")

    elif cmd == "streak":
        from bujo.analytics import InsightsEngine
        from bujo.app import VAULT

        _reconfigure_stdout()
        engine = InsightsEngine(VAULT)
        s = engine.streak()
        if s == 0:
            print("No streak yet. Log something today to start one.")
        elif s == 1:
            print("1 day. Start logging daily to build a streak.")
        else:
            print(f"{s} day streak. The habit is forming.")

    elif cmd == "vault":
        from bujo.app import VAULT

        print(str(VAULT))

    elif cmd == "tutorial":
        try:
            _reconfigure_stdout()
        except Exception:
            pass
        print(TUTORIAL_TEXT)

    elif cmd == "dump":
        from bujo.ai import save_dump_and_parse, show_setup_instructions
        from bujo.app import SYMBOL_DISPLAY, ensure_vault, VAULT
        import re

        ensure_vault()
        _reconfigure_stdout()

        # Check for --retry flag
        if "--retry" in args:
            from bujo.app import today_path, read_text_safe
            from bujo.models import parse_entries

            p = today_path()
            if not p.exists():
                print("No log file for today.")
                return
            content = read_text_safe(p)
            # Find dump blocks that are NOT followed by structured entries
            # A processed block has t/x/n/e/*/>/k lines right after ## /dump
            unprocessed: list[str] = []
            lines = content.split("\n")
            i = 0
            while i < len(lines):
                if lines[i].strip() == "## dump":
                    # Collect dump text until ## /dump
                    dump_lines = []
                    i += 1
                    while i < len(lines) and lines[i].strip() != "## /dump":
                        dump_lines.append(lines[i])
                        i += 1
                    i += 1  # skip ## /dump
                    # Check if structured entries follow
                    has_entries = False
                    if i < len(lines):
                        next_line = lines[i].strip()
                        if next_line and next_line[0] in (
                            "t",
                            "x",
                            "n",
                            "e",
                            "*",
                            "k",
                            ">",
                        ):
                            has_entries = True
                    if not has_entries and dump_lines:
                        unprocessed.append("\n".join(dump_lines))
                else:
                    i += 1

            if not unprocessed:
                print("No unprocessed dump blocks found.")
                return
            print(f"Found {len(unprocessed)} unprocessed dump block(s) to re-parse...")
            from bujo.ai import retry_parse

            for raw_text in unprocessed:
                success, entries, err = retry_parse(raw_text, VAULT)
                if success:
                    _print_dump_entries(entries)
                elif err == "no_key":
                    show_setup_instructions()
                else:
                    print(f"  Error: {err}")
            return

        # Get text from args or stdin
        if len(args) >= 2:
            text = " ".join(args[1:])
        else:
            # Multiline input mode
            print(
                "dump mode — type freely, submit with Ctrl+Z (Windows) or Ctrl+D (Mac/Linux)"
            )
            print("\u2500" * 50)
            lines: list[str] = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass
            text = "\n".join(lines)

        if not text.strip():
            print("Empty input. Nothing to parse.")
            return

        # Save raw text first (nothing ever lost) — check key only for API call
        from bujo.ai import get_ai_config

        if get_ai_config() is None:
            # Still save the raw text to vault
            from bujo.app import today_path, today_log
            from datetime import date

            p = today_path()
            if not p.exists():
                today_log()
            with open(p, "a", encoding="utf-8") as f:
                f.write(f"\n## dump\n{text}\n## /dump\n")

            show_setup_instructions()
            print("\nYour text was saved as a draft in today's log.")
            print("Set your API key and run: bujo dump --retry")
            return

        print("\nparsing...")
        success, entries, err = save_dump_and_parse(text, VAULT)

        if success:
            print(f"\nparsed {len(entries)} entries:\n")
            _print_dump_entries(entries)
            from bujo.app import today_path

            print(f"\nsaved to {today_path()}")
        elif err == "no_key":
            print("\n")
            show_setup_instructions()
            print("\nYour text was saved as a draft in today's log.")
            print("Set your API key and run: bujo dump --retry")
        else:
            print(f"\nError: {err}")
            print("Your text was saved as a draft in today's log.")
            print("Set your API key and run: bujo dump --retry")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
