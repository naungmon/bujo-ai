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
    bujo help                 Show usage
"""

import sys
import json
import os


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
        sys.stdout.reconfigure(encoding="utf-8")
        print(f"Added: {d} {text}")

    elif cmd == "log":
        from bujo.app import today_log, ensure_vault

        ensure_vault()
        sys.stdout.reconfigure(encoding="utf-8")
        print(today_log())

    elif cmd == "summary":
        from bujo.app import get_all_logs_summary, ensure_vault

        ensure_vault()
        sys.stdout.reconfigure(encoding="utf-8")
        print(get_all_logs_summary())

    elif cmd == "coach":
        from bujo.analytics import InsightsEngine
        from bujo.app import VAULT

        engine = InsightsEngine(VAULT)
        report = engine.full_report()
        sys.stdout.reconfigure(encoding="utf-8")

        if "--human" in args:
            _print_coach_human(report)
        else:
            print(json.dumps(report, indent=2))

    elif cmd == "week":
        from bujo.analytics import InsightsEngine
        from bujo.app import VAULT

        engine = InsightsEngine(VAULT)
        week = engine.weekly_summary()
        sys.stdout.reconfigure(encoding="utf-8")

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

        sys.stdout.reconfigure(encoding="utf-8")
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
        sys.stdout.reconfigure(encoding="utf-8")
        print(f"Added: {d} {cleaned}")

    elif cmd == "template" and len(args) >= 2:
        from bujo.capture import apply_template
        from bujo.app import append_entry, ensure_vault, VAULT

        ensure_vault()
        template_name = args[1]
        entries = apply_template(template_name, VAULT)

        if not entries:
            sys.stdout.reconfigure(encoding="utf-8")
            print(f"Template '{template_name}' not found or empty.")
            print("Available: morning, evening, weekly")
            return

        for symbol, text in entries:
            append_entry(symbol, text)

        sys.stdout.reconfigure(encoding="utf-8")
        print(f"Applied template '{template_name}' ({len(entries)} entries)")

    elif cmd == "streak":
        from bujo.analytics import InsightsEngine
        from bujo.app import VAULT

        sys.stdout.reconfigure(encoding="utf-8")
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

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
