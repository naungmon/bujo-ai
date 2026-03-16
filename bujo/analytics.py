"""Analytics engine for BuJo logs."""

from collections import Counter
from datetime import date, timedelta, datetime
from pathlib import Path

from bujo.models import LogReader, DayLog, Entry


class InsightsEngine:
    """Analyzes BuJo logs and generates insights."""

    def __init__(self, vault: Path):
        self.vault = vault
        self.reader = LogReader(vault)

    def migration_patterns(self) -> list[dict]:
        """Find tasks migrated 3+ times. Returns {text, count, first_seen, last_seen}."""
        all_logs = self.reader.load_all()
        task_counts: dict[str, dict] = {}

        for log in all_logs:
            for entry in log.entries:
                if entry.symbol == ".":  # pending task
                    text_lower = entry.text.lower().strip()
                    if text_lower not in task_counts:
                        task_counts[text_lower] = {
                            "text": entry.text,
                            "count": 0,
                            "first_seen": log.date.isoformat(),
                            "last_seen": log.date.isoformat(),
                        }
                    task_counts[text_lower]["count"] += 1
                    task_counts[text_lower]["last_seen"] = log.date.isoformat()

        # Find tasks that appear as migrated (>) or pending (t) across many days
        migrated_tasks: dict[str, dict] = {}
        for log in all_logs:
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
        total_entries = sum(len(log.entries) for log in all_logs)
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

        themes = self.kill_themes()
        if themes:
            top_theme, top_count = next(iter(themes.items()))
            if top_count >= 3:
                return f"You tend to drop {top_theme} tasks ({top_count} times). Worth examining why."

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
        total_entries = sum(len(log.entries) for log in logs)

        return {
            "period": f"{(date.today() - timedelta(days=6)).isoformat()} to {date.today().isoformat()}",
            "streak": self.streak(),
            "momentum": self.momentum_score(),
            "completion_rate_7d": round(self.done_pending_ratio(7), 2),
            "priority_alignment_7d": round(self.priority_alignment(7), 2),
            "total_entries_7d": total_entries,
            "stuck_tasks": self.migration_patterns()[:5],
            "kill_themes": self.kill_themes(),
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

        top_bucket = max(buckets, key=buckets.get)
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
        total_logged = sum(len(log.entries) for log in logs)
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
