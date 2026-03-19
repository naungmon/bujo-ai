"""Redesigned DailyView — modeless, focus-based interaction.

No nav_mode toggle. Arrow keys naturally move between input and entry list.
Focus determines what keys do. Inline editing via EntryItem.
"""

from datetime import date, timedelta
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical, Horizontal
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Input, ListView, Static, TextArea
from textual import events, on, work

from bujo.models import LogReader, parse_entries
from bujo.symbols import SYMBOLS, SYMBOL_DISPLAY, SYMBOL_COLORS, ENTRY_SORT_ORDER
from bujo.vault import (
    VAULT, DAILY, FIRST_RUN_FLAG,
    ensure_vault, today_path, today_log, save_today, append_entry,
    read_text_safe, has_any_daily_files, load_yesterday_pending,
)
from bujo.undo import UndoAction, UndoStack
from bujo.hints import HintManager
from bujo.widgets.input_bar import BuJoInput
from bujo.widgets.entry_list import BuJoListView, EntryItem, format_entry
from bujo.widgets.date_ribbon import DateRibbon


class DailyView(Screen):
    """Main daily log — modeless interaction, focus-based key handling."""

    dump_mode = reactive(False)

    BINDINGS = [
        Binding("ctrl+b", "coach", "Coach"),
        Binding("ctrl+d", "dump", "Dump"),
        Binding("ctrl+z", "undo", "Undo"),
        Binding("ctrl+delete", "clear_today", "Clear today"),
    ]

    _first_run_tour_pending: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        with Vertical(id="daily-layout"):
            yield DateRibbon(id="date-ribbon")
            yield Static("", id="greeting-label")
            yield Static("", id="count-label")
            yield Static("", id="past-day-indicator")
            yield Static("\u2500" * 48, id="separator")
            yield ScrollableContainer(
                Static(
                    "[dim italic]just start typing[/dim italic]",
                    id="empty-hint",
                ),
                BuJoListView(id="entry-list"),
                id="entry-scroll",
                can_focus=False,
            )
            yield Static("", id="inline-display")
            yield Static("", id="hint-bar")
            with Horizontal(id="input-row"):
                yield Static("[bold cyan]\u25b8 [/bold cyan]", id="input-prompt")
                yield BuJoInput("", id="main-input", show_line_numbers=False)
            # Dump mode (hidden initially)
            yield Static(
                "[dim italic]dump mode[/dim italic]", id="dump-label"
            )
            yield TextArea(id="dump-input")

    def on_mount(self) -> None:
        self._current_coach_mode = False
        self._clear_confirm_pending = False
        self._undo_stack = UndoStack()
        self._hint_manager = HintManager()
        self._session_entry_count = 0
        self._pending_migration: list[dict] = []
        self._migration_mode = False
        self._load_day()
        # Check API key
        from bujo.ai_capture import OPENROUTER_API_KEY
        if not OPENROUTER_API_KEY:
            self.notify("OPENROUTER_API_KEY not set \u2014 AI capture disabled", severity="warning", timeout=5)
        # Always focus input
        self.set_timer(0.1, self._focus_input)

    def _focus_input(self) -> None:
        try:
            self.query_one("#main-input", BuJoInput).focus()
        except Exception:
            pass

    # ── Date navigation ────────────────────────────────

    def _viewing_date(self) -> date:
        return self.query_one("#date-ribbon", DateRibbon).viewing_date

    def _set_viewing_date(self, d: date) -> None:
        self.query_one("#date-ribbon", DateRibbon).viewing_date = d

    def _day_path(self, d: date) -> Path:
        return DAILY / f"{d.isoformat()}.md"

    def _day_log(self, d: date) -> str:
        p = self._day_path(d)
        if d == date.today():
            return today_log()
        if p.exists():
            return read_text_safe(p)
        return ""

    def _load_day(self) -> None:
        """Load entries for the currently viewed day."""
        from bujo.analytics import InsightsEngine
        from bujo.time import session_greeting

        d = self._viewing_date()
        content = self._day_log(d)
        p = self._day_path(d)
        entries = parse_entries(content, p, d) if content else []

        done = sum(1 for e in entries if e.symbol == "x")
        pending = sum(1 for e in entries if e.symbol == "t")
        priority = sum(1 for e in entries if e.symbol == "*")

        # Greeting — only show for today
        indicator = self.query_one("#past-day-indicator", Static)
        if d == date.today():
            engine = InsightsEngine(VAULT)
            s = engine.streak()
            greeting = session_greeting(streak=s, pending_count=pending)
            self.query_one("#greeting-label", Static).update(f"{greeting}")
            self.query_one("#greeting-label", Static).display = True
            indicator.update("")
            indicator.display = False
        else:
            self.query_one("#greeting-label", Static).display = False
            indicator.update(
                f"[yellow]viewing {d.strftime('%b %d')} \u00b7 typing saves to today[/yellow]"
            )
            indicator.display = True

        # Entry list
        lv = self.query_one("#entry-list", BuJoListView)
        lv.clear()
        lv.index = 0

        empty_hint = self.query_one("#empty-hint", Static)
        inline = self.query_one("#inline-display", Static)
        inline.update("")
        inline.display = False

        if not entries:
            empty_hint.display = True
            lv.display = False
            if d == date.today():
                self._pending_migration = load_yesterday_pending()
                if self._pending_migration:
                    self._migration_mode = True
                    empty_hint.display = False
                    lv.display = True
                    self.query_one("#greeting-label", Static).update(
                        "[bold]Yesterday's unfinished[/bold]"
                    )
                    for i, p in enumerate(self._pending_migration):
                        lv.append(EntryItem(p, i))
                    if lv.children:
                        lv.index = 0
                    count = len(self._pending_migration)
                    self.query_one("#count-label", Static).update(
                        f"[dim italic]{count} from yesterday · "
                        f"> migrate · k kill · r keep[/dim italic]"
                    )
                    self._update_hint_bar_migration()
                    return
                else:
                    self.query_one("#count-label", Static).update(
                        "[dim italic]no entries yet[/dim italic]"
                    )
            else:
                self.query_one("#count-label", Static).update(
                    "[dim italic]no entries on this day[/dim italic]"
                )
        else:
            empty_hint.display = False
            lv.display = True
            sorted_entries = sorted(entries, key=lambda e: ENTRY_SORT_ORDER.get(e.symbol, 99))
            for i, e in enumerate(sorted_entries):
                lv.append(
                    EntryItem(
                        {
                            "symbol": e.symbol,
                            "display": e.display,
                            "text": e.text,
                            "type": e.type,
                            "raw": e.raw,
                        },
                        i,
                    )
                )
            if lv.children:
                lv.index = min(lv.index or 0, len(lv.children) - 1)
            self.query_one("#count-label", Static).update(
                f"[dim]{done} done[/dim]  [dim]\u00b7[/dim]  "
                f"[dim]{pending} pending[/dim]  [dim]\u00b7[/dim]  "
                f"[dim]{priority} priority[/dim]"
            )

        # First-run check
        if not FIRST_RUN_FLAG.exists() and not has_any_daily_files():
            self._show_first_run()

        self._update_hint_bar()

    def _show_first_run(self) -> None:
        self._first_run_tour_pending = True
        greeting = self.query_one("#greeting-label", Static)
        greeting.display = True
        greeting.update(
            "[bold]BuJo \u2014 your ADHD journal[/bold]\n\n"
            f"[dim]vault ready at {VAULT}[/dim]\n\n"
            "[dim]just start typing. prefix is optional:[/dim]\n"
            "[cyan]t[/cyan] or [cyan]task[/cyan]      \u2192 task\n"
            "[magenta]e[/magenta] or [magenta]event[/magenta]     \u2192 event\n"
            "[white]n[/white] or [white]note[/white]      \u2192 note\n"
            "[red]*[/red] or [red]priority[/red]  \u2192 priority\n"
            "[dim italic](no prefix)      \u2192 note[/dim italic]\n\n"
            "[dim]anything with ! at the end becomes a priority.[/dim]\n\n"
            "[dim]press any key for a 2-min tour \u00b7 Escape to skip[/dim]"
        )

    def _update_hint_bar(self) -> None:
        hint = self.query_one("#hint-bar", Static)
        hint.update(
            "[dim]x done[/dim]  "
            "[dim]k kill[/dim]  "
            "[dim]> migrate[/dim]  "
            "[dim][ ] days[/dim]  "
            "[dim]/ search[/dim]  "
            "[dim]? help[/dim]  "
            "[dim]q quit[/dim]"
        )

    def _update_hint_bar_migration(self) -> None:
        hint = self.query_one("#hint-bar", Static)
        hint.update(
            "[dim]> migrate[/dim]  "
            "[dim]k kill[/dim]  "
            "[dim]r keep[/dim]  "
            "[dim]x done[/dim]  "
            "[dim]↑↓ navigate[/dim]"
        )

    def _remove_pending_item(self, idx: int) -> None:
        self._pending_migration.pop(idx)
        lv = self.query_one("#entry-list", BuJoListView)
        if lv.children and idx < len(lv.children):
            lv.children[idx].remove()
        if not self._pending_migration:
            self._migration_mode = False
            self._pending_migration = []
            self._load_day()

    def _rewrite_source(self, entry: dict, new_sym: str) -> None:
        f = entry["source_file"]
        content = read_text_safe(f)
        new_line = f"{new_sym} {entry['text']}"
        content = content.replace(entry["raw"], new_line, 1)
        f.write_text(content, encoding="utf-8")

    def _do_migrate_pending(self) -> None:
        lv = self.query_one("#entry-list", BuJoListView)
        if lv.index is None or lv.index >= len(self._pending_migration):
            return
        entry = self._pending_migration[lv.index]
        append_entry("t", entry["text"])
        self._rewrite_source(entry, ">")
        self._remove_pending_item(lv.index)
        self.notify(f"→ today: {entry['text'][:40]}", timeout=2)

    def _do_kill_pending(self) -> None:
        lv = self.query_one("#entry-list", BuJoListView)
        if lv.index is None or lv.index >= len(self._pending_migration):
            return
        entry = self._pending_migration[lv.index]
        today_str = date.today().isoformat()
        append_entry("k", f"{today_str} {entry['text']}")
        self._rewrite_source(entry, ">")
        self._remove_pending_item(lv.index)
        self.notify(f"killed {entry['text'][:40]}", timeout=2)

    def _do_keep_pending(self) -> None:
        lv = self.query_one("#entry-list", BuJoListView)
        if lv.index is None or lv.index >= len(self._pending_migration):
            return
        entry = self._pending_migration[lv.index]
        append_entry("t", entry["text"])
        self._rewrite_source(entry, ">")
        self._remove_pending_item(lv.index)
        self.notify(f"→ today: {entry['text'][:40]}", timeout=2)

    def _do_done_pending(self) -> None:
        lv = self.query_one("#entry-list", BuJoListView)
        if lv.index is None or lv.index >= len(self._pending_migration):
            return
        entry = self._pending_migration[lv.index]
        today_str = date.today().isoformat()
        append_entry("x", f"{today_str} {entry['text']}")
        self._rewrite_source(entry, ">")
        self._remove_pending_item(lv.index)
        self.notify(f"done: {entry['text'][:40]}", timeout=2)

    # ── Entry submission ───────────────────────────────

    @work(thread=True)
    def _submit_new_entry(self, text: str) -> None:
        """Parse and save entry, running AI call in worker thread."""
        from bujo.ai_capture import smart_parse

        # Show thinking indicator
        def show_thinking():
            try:
                self.query_one("#input-prompt", Static).update("[dim]thinking...[/dim]")
            except Exception:
                pass
        self.app.call_from_thread(show_thinking)

        entries_to_write = smart_parse(text)

        def finish():
            try:
                self.query_one("#input-prompt", Static).update("[bold cyan]\u25b8 [/bold cyan]")
            except Exception:
                pass

            for symbol, cleaned in entries_to_write:
                append_entry(symbol, cleaned)
                # Record undo
                self._undo_stack.push(UndoAction(
                    action_type="add",
                    file_path=today_path(),
                    original_line="",
                    new_line=f"{symbol} {cleaned}",
                    description=f'add "{cleaned[:30]}"',
                ))

            if not FIRST_RUN_FLAG.exists():
                FIRST_RUN_FLAG.write_text("done\n", encoding="utf-8")

            # Count entries for hints
            self._session_entry_count += len(entries_to_write)
            hint = self._hint_manager.check_entry_count(self._session_entry_count)
            if hint:
                self.notify(hint, timeout=5)

            # Auto-switch to today if viewing past day
            if self._viewing_date() != date.today():
                self._set_viewing_date(date.today())

            self._load_day()
            self._focus_input()

        self.app.call_from_thread(finish)

    # ── Inline editing ─────────────────────────────────

    def _save_inline_edit(self, item: EntryItem, new_text: str) -> None:
        """Save an inline edit, updating the markdown file."""
        entry = item.entry
        old_raw = entry.get("raw", "") if isinstance(entry, dict) else entry.raw
        sym = entry.get("symbol", "n") if isinstance(entry, dict) else entry.symbol
        old_text = entry.get("text", "") if isinstance(entry, dict) else entry.text

        new_line = f"{sym} {new_text}"
        content = self._day_log(self._viewing_date())
        content = content.replace(old_raw, new_line, 1)

        d = self._viewing_date()
        self._day_path(d).write_text(content, encoding="utf-8")

        self._undo_stack.push(UndoAction(
            action_type="edit",
            file_path=self._day_path(d),
            original_line=old_raw,
            new_line=new_line,
            description=f'edit "{old_text[:20]}" \u2192 "{new_text[:20]}"',
        ))

        item.cancel_edit()
        self._load_day()

    # ── Status changes ─────────────────────────────────

    def _get_selected_entry(self) -> dict | None:
        lv = self.query_one("#entry-list", BuJoListView)
        if lv.index is None:
            return None
        d = self._viewing_date()
        content = self._day_log(d)
        entries = parse_entries(content, self._day_path(d), d) if content else []
        sorted_entries = sorted(entries, key=lambda e: ENTRY_SORT_ORDER.get(e.symbol, 99))
        if lv.index >= len(sorted_entries):
            return None
        e = sorted_entries[lv.index]
        return {"symbol": e.symbol, "text": e.text, "raw": e.raw, "type": e.type}

    def _rewrite_entry(self, old_raw: str, new_sym: str, text: str) -> None:
        d = self._viewing_date()
        content = self._day_log(d)
        new_line = f"{new_sym} {text}"
        content = content.replace(old_raw, new_line, 1)
        self._day_path(d).write_text(content, encoding="utf-8")

        self._undo_stack.push(UndoAction(
            action_type="status_change",
            file_path=self._day_path(d),
            original_line=old_raw,
            new_line=new_line,
            description=f'{new_sym} "{text[:25]}"',
        ))

    def _do_status_change(self, new_sym: str, label: str) -> None:
        entry = self._get_selected_entry()
        if entry is None:
            return
        self._rewrite_entry(entry["raw"], new_sym, entry["text"])
        self.notify(f"{label}: {entry['text'][:40]}", timeout=2)
        self._load_day()

    # ── Undo ───────────────────────────────────────────

    def action_undo(self) -> None:
        result = self._undo_stack.undo()
        if result is None:
            self.notify("nothing to undo", timeout=2)
            return
        self.notify(f"undid: {result.description}", timeout=3)
        self._load_day()

    # ── Coach ──────────────────────────────────────────

    @work(thread=True)
    def action_coach(self) -> None:
        from bujo.analytics import InsightsEngine

        engine = InsightsEngine(VAULT)
        reader = LogReader(VAULT)
        all_logs = reader.load_all()
        total = sum(len(log.entries) for log in all_logs)

        self.app.call_from_thread(self._show_coach, engine, total)

    def _show_coach(self, engine, total: int) -> None:
        self._current_coach_mode = True

        inline = self.query_one("#inline-display", Static)
        lv = self.query_one("#entry-list", BuJoListView)
        empty = self.query_one("#empty-hint", Static)

        lv.display = False
        empty.display = False
        inline.display = True

        if total < 5:
            remaining = 5 - total
            inline.update(
                f"\n[dim italic]write {remaining} more entr{'y' if remaining == 1 else 'ies'} first.\n"
                f"i'll have something to say after 5.\n\n"
                f"you have {total} so far.[/dim italic]\n\n"
                f"[dim italic]any key to close[/dim italic]"
            )
        else:
            report = engine.full_report()
            lines = [
                "",
                "[dim italic]\u2500\u2500 coach " + "\u2500" * 41 + "[/dim italic]",
                "",
                f"  momentum      {report['momentum']}",
                f"  streak        {report['streak']} day{'s' if report['streak'] != 1 else ''}",
                f"  done today    {sum(1 for e in parse_entries(today_log(), today_path(), date.today()) if e.symbol == 'x')}",
                "",
            ]

            stuck = report.get("stuck_tasks", [])
            if stuck:
                lines.append("[dim italic]  stuck[/dim italic]")
                for t in stuck[:3]:
                    lines.append(
                        f"  \u00b7 {t['text']}  [dim]moved {t['count']} times[/dim]"
                    )
                lines.append("")

            themes = report.get("kill_themes", {})
            if themes:
                lines.append("[dim italic]  dropping[/dim italic]")
                for theme, count in list(themes.items())[:2]:
                    lines.append(f"  {theme} tasks  [dim]killed {count} times[/dim]")
                lines.append("")

            productive = report.get("most_productive_time", "not enough data")
            if "not enough" not in productive:
                lines.append("[dim italic]  most productive[/dim italic]")
                lines.append(f"  {productive}")
                lines.append("")

            lines.append("[dim italic]" + "\u2500" * 48 + "[/dim italic]")
            lines.append("")
            lines.append(f"  [cyan]{report['nudge']}[/cyan]")
            lines.append("")
            lines.append("[dim italic]any key to close[/dim italic]")
            inline.update("\n".join(lines))

    def _close_coach(self) -> None:
        self._current_coach_mode = False
        inline = self.query_one("#inline-display", Static)
        inline.update("")
        inline.display = False
        self._load_day()
        self._focus_input()

    # ── Dump mode ──────────────────────────────────────

    def action_dump(self) -> None:
        self._enter_dump_mode()

    def _enter_dump_mode(self) -> None:
        self.dump_mode = True
        try:
            self.query_one("#input-row", Horizontal).display = False
        except Exception:
            pass
        try:
            self.query_one("#dump-input", TextArea).display = True
            self.query_one("#dump-label", Static).display = True
            self.query_one("#dump-input", TextArea).focus()
        except Exception:
            pass

    def _exit_dump_mode(self) -> None:
        self.dump_mode = False
        try:
            self.query_one("#dump-input", TextArea).display = False
            self.query_one("#dump-label", Static).display = False
        except Exception:
            pass
        try:
            self.query_one("#input-row", Horizontal).display = True
        except Exception:
            pass
        self._focus_input()

    @work(thread=True)
    def _submit_dump(self) -> None:
        from bujo.ai import save_dump_and_parse, get_ai_config

        try:
            text_area = self.query_one("#dump-input", TextArea)
            text = text_area.text
        except Exception:
            return

        if not text.strip():
            self.app.call_from_thread(self._exit_dump_mode)
            return

        success, entries, err = save_dump_and_parse(text, VAULT)

        if success:
            type_map = {"t": "task", "n": "note", "e": "event", "*": "priority", "x": "done"}
            lines = ["", f"[dim italic]parsed {len(entries)} entries:[/dim italic]", ""]
            for sym, entry_text in entries:
                d = SYMBOL_DISPLAY.get(sym, sym)
                label = type_map.get(sym, sym)
                lines.append(f"  {d} {entry_text}  [dim italic]{label}[/dim italic]")
            inline_text = "\n".join(lines)

            def show_result():
                self._exit_dump_mode()
                inline = self.query_one("#inline-display", Static)
                inline.update(inline_text)
                inline.display = True
                self._load_day()

            self.app.call_from_thread(show_result)
        elif err == "no_key":
            def show_key_error():
                self._exit_dump_mode()
                inline = self.query_one("#inline-display", Static)
                inline.update(
                    "[red]No API key set.[/red]\n\n"
                    "[dim]Set BUJO_AI_KEY in your environment:\n"
                    '  $env:BUJO_AI_KEY="sk-or-..."\n\n'
                    "Get a key at openrouter.ai/keys[/dim]"
                )
                inline.display = True
            self.app.call_from_thread(show_key_error)
        else:
            def show_other_error():
                self._exit_dump_mode()
                inline = self.query_one("#inline-display", Static)
                inline.update(
                    f"[red]Error: {err}[/red]\n[dim italic]Draft saved in log. Try: bujo dump --retry[/dim italic]"
                )
                inline.display = True
            self.app.call_from_thread(show_other_error)

    # ── Clear today ────────────────────────────────────

    def action_clear_today(self) -> None:
        if not self._clear_confirm_pending:
            self._clear_confirm_pending = True
            self.notify("Press Ctrl+Delete again to confirm clearing today's entries", severity="warning", timeout=4)
            self.set_timer(4, lambda: setattr(self, "_clear_confirm_pending", False))
            return
        p = today_path()
        if p.exists():
            header = f"# {date.today().strftime('%A, %B %d %Y')}\n\n"
            p.write_text(header, encoding="utf-8")
        self._clear_confirm_pending = False
        self.notify("Today's entries cleared", severity="information", timeout=3)
        self._load_day()

    # ── Key handling — focus-based ─────────────────────

    @on(Input.Submitted, "#inline-edit")
    def on_inline_edit_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter during inline edit."""
        new_text = event.value.strip()
        if not new_text:
            return
        # Find the EntryItem that contains this Input
        lv = self.query_one("#entry-list", BuJoListView)
        for child in lv.children:
            if isinstance(child, EntryItem) and child.is_editing:
                self._save_inline_edit(child, new_text)
                break

    def on_key(self, event: events.Key) -> None:
        # Tour prompt intercept — any key (except Escape) starts the tour
        if self._first_run_tour_pending:
            self._first_run_tour_pending = False
            if event.key != "escape":
                from bujo.views.tutorial import TutorialScreen
                self.app.push_screen(TutorialScreen())
            return

        # Coach dismiss
        if self._current_coach_mode:
            if event.key != "ctrl+b":
                self._close_coach()
                event.stop()
            return

        # Dump mode
        if self.dump_mode:
            if event.key == "escape":
                self._exit_dump_mode()
                event.stop()
                return
            if event.key == "enter":
                self._submit_dump()
                event.stop()
                return
            return

        key = event.key
        inp = self.query_one("#main-input", BuJoInput)
        lv = self.query_one("#entry-list", BuJoListView)

        # ── Enter key disambiguation ──
        if key == "enter":
            if inp.has_focus:
                text = inp.text.strip()
                if text:
                    inp.load_text("")
                    self._submit_new_entry(text)
                event.stop()
                return
            if lv.has_focus:
                highlighted = lv.highlighted_child
                if highlighted and isinstance(highlighted, EntryItem):
                    if highlighted.is_editing:
                        return  # Input.Submitted handles this
                    highlighted.start_edit()
                event.stop()
                return

        # ── Escape — cancel edit or do nothing ──
        if key == "escape":
            # Cancel inline edit if active
            for child in lv.children:
                if isinstance(child, EntryItem) and child.is_editing:
                    child.cancel_edit()
                    lv.focus()
                    event.stop()
                    return
            # Otherwise, focus input
            self._focus_input()
            event.stop()
            return

        # ── Date navigation ──
        if key == "left_square_bracket":
            ribbon = self.query_one("#date-ribbon", DateRibbon)
            ribbon.go_prev()
            # First nav hint
            hint = self._hint_manager.check("first_nav")
            if hint:
                self.notify(hint, timeout=5)
            # Multi-day hint
            hint2 = self._hint_manager.check("multi_day")
            if hint2:
                self.notify(hint2, timeout=5)
            self._load_day()
            event.stop()
            return
        if key == "right_square_bracket":
            ribbon = self.query_one("#date-ribbon", DateRibbon)
            ribbon.go_next()
            self._load_day()
            event.stop()
            return

        # ── Search ──
        if key == "slash":
            if not inp.has_focus or not inp.text.strip():
                from bujo.views.search import SearchView
                def on_search_result(target_date) -> None:
                    if target_date and isinstance(target_date, date):
                        self._set_viewing_date(target_date)
                        self._load_day()
                self.app.push_screen(SearchView(), callback=on_search_result)
                event.stop()
                return

        # ── Status changes — only when list has focus and not editing ──
        if lv.has_focus:
            editing = any(
                isinstance(c, EntryItem) and c.is_editing for c in lv.children
            )
            if not editing:
                if self._migration_mode and self._pending_migration:
                    if key == "greater_than_sign":
                        self._do_migrate_pending()
                        event.stop()
                        return
                    if key == "k":
                        self._do_kill_pending()
                        event.stop()
                        return
                    if key == "r":
                        self._do_keep_pending()
                        event.stop()
                        return
                    if key == "x":
                        self._do_done_pending()
                        event.stop()
                        return
                else:
                    if key == "x":
                        self._do_status_change("x", "done")
                        event.stop()
                        return
                    if key == "k":
                        self._do_status_change("k", "killed")
                        event.stop()
                        return
                    if key == "greater_than_sign":
                        self._do_status_change(">", "migrated")
                        event.stop()
                        return

        # ── Screen navigation (always available except during edit) ──
        if key == "m" and not inp.has_focus:
            from bujo.views.monthly import MonthlyView
            self.app.push_screen(MonthlyView())
            event.stop()
            return
        if key == "f" and not inp.has_focus:
            from bujo.views.future import FutureView
            self.app.push_screen(FutureView())
            event.stop()
            return
        if key == "shift+m" and not inp.has_focus:
            from bujo.views.migration import MigrationScreen
            self.app.push_screen(MigrationScreen())
            event.stop()
            return
        if key == "shift+r" and not inp.has_focus:
            from bujo.views.review import ReviewView
            self.app.push_screen(ReviewView())
            event.stop()
            return
        if key == "question_mark" and not inp.has_focus:
            from bujo.views.help import HelpScreen
            self.app.push_screen(HelpScreen())
            event.stop()
            return
        if key == "q" and not inp.has_focus:
            self.app.exit()
            event.stop()
            return
