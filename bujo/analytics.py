"""Analytics engine for BuJo logs."""

from collections import Counter
from datetime import date, timedelta, datetime
from pathlib import Path
import re

from bujo.models import LogReader, DayLog, Entry


class InsightsEngine:
    """Analyzes BuJo logs and generates insights."""

    def __init__(self, vault: Path):
        self.vault = vault
        self.reader = LogReader(vault)

    def migration_patterns(self) -> list[dict]:
        """Find tasks migrated 3+ times. Returns {text, count, first_seen, last_seen}."""
        migrated_tasks: dict[str, dict] = {}
        for log in self.reader.load_all():
            for entry in log.entries:
                if entry.symbol in ("t", ">"):
                    text_lower = entry.text.lower().strip()
                    if text_lower not in migrated_tasks:
                        migrated_tasks[text_lower] = {
                            "text": entry.text,
                            "count": 0,
                            "first_seen": log.date.isoformat(),
                            "last_seen": log.date.isoformat(),
                        }
                    migrated_tasks[text_lower]["count"] += 1
                    migrated_tasks[text_lower]["last_seen"] = log.date.isoformat()

        stuck = [v for v in migrated_tasks.values() if v["count"] >= 3]
        stuck.sort(key=lambda x: x["count"], reverse=True)
        return stuck

    def kill_themes(self) -> dict[str, int]:
        """Group killed entries by first word. Returns {theme: count}."""
        all_logs = self.reader.load_all()
        themes: list[str] = []

        for log in all_logs:
            for entry in log.entries:
                if entry.symbol == "k":
                    words = entry.text.lower().split()
                    if words:
                        theme = words[0]
                        themes.append(theme)

        return dict(Counter(themes).most_common(10))

    def done_pending_ratio(self, days: int = 7) -> float:
        """Completion velocity: done / (done + pending) over last N days."""
        logs = self.reader.load_range(days)
        total_done = sum(len(log.done) for log in logs)
        total_pending = sum(len(log.pending) for log in logs)
        total = total_done + total_pending
        return total_done / total if total > 0 else 0.0

    def priority_alignment(self, days: int = 7) -> float:
        """What % of * entries became x within the same day's log."""
        logs = self.reader.load_range(days)
        total_priorities = 0
        done_priorities = 0

        for log in logs:
            priority_texts = {e.text.lower() for e in log.priorities}
            done_texts = {e.text.lower() for e in log.done}
            total_priorities += len(priority_texts)
            done_priorities += len(priority_texts & done_texts)

        return done_priorities / total_priorities if total_priorities > 0 else 0.0

    def momentum_score(self) -> str:
        """Compare this week vs last week completion rates."""
        this_week = self.done_pending_ratio(7)
        last_week_logs = self.reader.load_range(14)
        last_week_done = sum(len(log.done) for log in last_week_logs[:7])
        last_week_pending = sum(len(log.pending) for log in last_week_logs[:7])
        last_week_total = last_week_done + last_week_pending
        last_week = last_week_done / last_week_total if last_week_total > 0 else 0.0

        all_logs = self.reader.load_range(7)
        total_entries = sum(
            len([e for e in log.entries if e.symbol != "<"]) for log in all_logs
        )
        if total_entries < 3:
            return "new"

        if this_week < 0.2 and last_week < 0.2:
            return "stalled"
        elif this_week < last_week - 0.2:
            return "stalling"
        elif this_week > last_week + 0.2:
            return "building"
        else:
            return "steady"

    def streak(self) -> int:
        """Consecutive days with at least 1 entry, counting back from today."""
        count = 0
        today = date.today()

        for i in range(365):  # max 1 year streak
            d = today - timedelta(days=i)
            log = self.reader.load_day(d)
            if len(log.entries) > 0:
                count += 1
            else:
                break

        return count

    def coaching_nudge(self) -> str:
        """Single most important sentence based on data."""
        stuck = self.migration_patterns()
        if stuck and stuck[0]["count"] >= 4:
            return f'You\'ve migrated "{stuck[0]["text"]}" {stuck[0]["count"]} times. Kill it or do it today.'

        overcommit = self.event_heavy_day_nudge()
        if overcommit:
            return overcommit

        themes = self.kill_themes()
        if themes:
            top_theme, top_count = next(iter(themes.items()))
            if top_count >= 3:
                stats = self.stall_stats(theme=top_theme)
                if stats["count"] >= 3 and stats["avg"] > 0:
                    return f"You carried '{top_theme}' for {stats['avg']} days on average before dropping ({top_count} times)."
                return f"You tend to drop {top_theme} tasks ({top_count} times). Worth examining why."

        heavy_days = self.note_heavy_days()
        if len(heavy_days) >= 2:
            dates = ", ".join(d["date"][:10] for d in heavy_days[:2])
            return f"Heavy note days: {dates} — dumps, not daily rhythm. What's triggering them?"

        alignment = self.priority_alignment()
        if alignment < 0.4:
            return "You're setting priorities but not finishing them. Fewer priorities, more action."

        momentum = self.momentum_score()
        if momentum == "building":
            return "Completion rate is up this week. Keep going."
        elif momentum == "stalled":
            return "Completion rate is low. Pick one small thing and finish it."

        s = self.streak()
        if s >= 7:
            return f"{s}-day streak. The habit is forming."

        return "No patterns yet. Keep logging."

    def full_report(self) -> dict:
        """Structured output for bujo coach command."""
        logs = self.reader.load_range(7)
        total_entries = sum(
            len([e for e in log.entries if e.symbol != "<"]) for log in logs
        )

        stall = self.stall_stats()
        event_map = self.event_density_mapping()
        heavy_days = self.note_heavy_days()

        return {
            "period": f"{(date.today() - timedelta(days=6)).isoformat()} to {date.today().isoformat()}",
            "streak": self.streak(),
            "momentum": self.momentum_score(),
            "completion_rate_7d": round(self.done_pending_ratio(7), 2),
            "priority_alignment_7d": round(self.priority_alignment(7), 2),
            "total_entries_7d": total_entries,
            "stuck_tasks": self.migration_patterns()[:5],
            "kill_themes": self.kill_themes(),
            "avg_stall_days": stall["avg"],
            "event_density_mapping": event_map,
            "note_heavy_days_14d": [d["date"] for d in heavy_days],
            "nudge": self.coaching_nudge(),
            "empty": total_entries < 3,
            "most_productive_time": self.most_productive_time(),
            "tasks_per_day_avg": round(self.tasks_per_day_avg(), 1),
        }

    def most_productive_time(self) -> str:
        """Determine most productive time bucket based on file modification times.

        Uses file mtime as a proxy for when entries were made. Returns bucket
        with highest activity: morning (5-12), afternoon (12-17), evening (17-21), late (21-5).
        """
        buckets: dict[str, int] = {
            "morning": 0,
            "afternoon": 0,
            "evening": 0,
            "late": 0,
        }
        total_entries_with_time = 0

        for log in self.reader.load_range(30):
            if not log.entries:
                continue
            try:
                mtime = log.path.stat().st_mtime
                hour = datetime.fromtimestamp(mtime).hour
            except (OSError, AttributeError):
                continue

            if 5 <= hour < 12:
                bucket = "morning"
            elif 12 <= hour < 17:
                bucket = "afternoon"
            elif 17 <= hour < 21:
                bucket = "evening"
            else:
                bucket = "late"

            buckets[bucket] += len(log.entries)
            total_entries_with_time += 1

        if total_entries_with_time < 3:
            return "not enough data"

        top_bucket = max(buckets, key=lambda k: buckets[k])  # type: ignore[arg-type]
        return f"{top_bucket} ({buckets[top_bucket]} entries from {total_entries_with_time} days)"

    def tasks_per_day_avg(self) -> float:
        """Average completed tasks per day, excluding empty days from denominator."""
        logs = self.reader.load_range(30)
        days_with_entries = 0
        total_done = 0

        for log in logs:
            if len(log.entries) > 0:
                days_with_entries += 1
                total_done += len(log.done)

        return total_done / days_with_entries if days_with_entries > 0 else 0.0

    def weekly_summary(self) -> dict:
        """Weekly summary with totals and insights."""
        logs = self.reader.load_range(7)
        total_logged = sum(
            len([e for e in log.entries if e.symbol != "<"]) for log in logs
        )
        total_done = sum(len(log.done) for log in logs)
        total_killed = sum(len(log.killed) for log in logs)
        total_migrated = sum(len(log.migrated) for log in logs)

        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)

        return {
            "week_range": f"{monday.strftime('%b %d')}\u2013{sunday.strftime('%d')}",
            "total_logged": total_logged,
            "total_done": total_done,
            "total_killed": total_killed,
            "total_migrated": total_migrated,
            "streak": self.streak(),
            "top_insight": self.coaching_nudge(),
            "most_productive_time": self.most_productive_time(),
        }

    def stall_duration(self, kill_entry_text: str) -> int | None:
        """Days from first t occurrence to kill date for a given task text.

        kill_entry_text is the full kill entry text, e.g. 'k 2026-03-12 gym session'.
        Returns None if task never appeared as t before being killed.
        """
        pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(.+)$")
        m = pattern.match(kill_entry_text)
        if not m:
            return None

        kill_date_str, task_text = m.group(1), m.group(2)
        task_lower = task_text.lower().strip()
        first_seen: date | None = None

        for log in self.reader.load_all():
            for entry in log.entries:
                if entry.symbol == "t" and entry.text.lower().strip() == task_lower:
                    if first_seen is None or log.date < first_seen:
                        first_seen = log.date

        if first_seen is None:
            return None

        try:
            kill_date = date.fromisoformat(kill_date_str)
        except ValueError:
            return None

        return (kill_date - first_seen).days

    def stall_stats(self, theme: str | None = None) -> dict:
        """Compute stall duration stats across killed entries.

        Parses k YYYY-MM-DD text format. Returns avg, median, max, count.
        If theme is set, filters to kills where first word matches.
        """
        durations: list[int] = []
        pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(.+)$")

        for log in self.reader.load_all():
            for entry in log.entries:
                if entry.symbol != "k":
                    continue
                m = pattern.match(entry.text)
                if not m:
                    continue
                kill_date_str, rest = m.group(1), m.group(2)
                words = rest.lower().split()
                if not words:
                    continue
                entry_theme = words[0]
                if theme is not None and entry_theme != theme.lower():
                    continue
                try:
                    date.fromisoformat(kill_date_str)
                except ValueError:
                    continue
                duration = self.stall_duration(entry.text)
                if duration is not None:
                    durations.append(duration)

        if not durations:
            return {"avg": 0.0, "median": 0.0, "max": 0, "count": 0}

        durations.sort()
        count = len(durations)
        avg = sum(durations) / count
        mid = count // 2
        median = durations[mid] if count % 2 == 1 else (durations[mid - 1] + durations[mid]) / 2

        return {
            "avg": round(avg, 1),
            "median": median,
            "max": max(durations),
            "count": count,
        }

    def event_density_mapping(self) -> dict:
        """Completion rate broken down by event count per day.

        Buckets: low (0-1 events), medium (2 events), high (3+ events).
        Returns {bucket: {"days": int, "completion_rate": float}}.
        """
        logs = self.reader.load_range(30)
        buckets: dict[str, dict] = {
            "low": {"days": 0, "done": 0, "pending": 0},
            "medium": {"days": 0, "done": 0, "pending": 0},
            "high": {"days": 0, "done": 0, "pending": 0},
        }

        for log in logs:
            event_count = len(log.events)
            if event_count <= 1:
                bucket = "low"
            elif event_count == 2:
                bucket = "medium"
            else:
                bucket = "high"

            buckets[bucket]["days"] += 1
            buckets[bucket]["done"] += len(log.done)
            buckets[bucket]["pending"] += len(log.pending)

        result = {}
        for bucket, data in buckets.items():
            total = data["done"] + data["pending"]
            rate = data["done"] / total if total > 0 else 0.0
            result[bucket] = {
                "days": data["days"],
                "completion_rate": round(rate, 2),
            }
        return result

    def event_heavy_day_nudge(self) -> str | None:
        """Check last 7 days for a day with 3+ events and 0 tasks done."""
        logs = self.reader.load_range(7)
        for log in logs:
            if len(log.events) >= 3 and len(log.done) == 0 and len(log.pending) > 0:
                return f"{len(log.events)} events on {log.date.strftime('%b %d')} and zero tasks done — overcommit alert."
        return None

    def note_density(self) -> list[dict]:
        """Per-day note counts over last 14 days.

        Returns [{"date": "YYYY-MM-DD", "count": int, "heavy": bool}].
        heavy = count >= 5.
        """
        logs = self.reader.load_range(14)
        result = []
        for log in logs:
            note_count = len([e for e in log.entries if e.symbol == "n"])
            result.append({
                "date": log.date.isoformat(),
                "count": note_count,
                "heavy": note_count >= 5,
            })
        return result

    def note_heavy_days(self) -> list[dict]:
        """Days in last 14 with 5+ notes, sorted by note count desc."""
        density = self.note_density()
        heavy = [d for d in density if d["heavy"]]
        heavy.sort(key=lambda x: x["count"], reverse=True)
        return heavy
