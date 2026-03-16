"""Time-aware utilities for BuJo."""

from datetime import datetime


def time_of_day_greeting() -> str:
    """Context-aware greeting based on current hour."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Morning. Set your intention for today."
    elif 12 <= hour < 17:
        return "Afternoon. How is today going?"
    elif 17 <= hour < 22:
        return "Evening. Good time to review."
    else:
        return "Late. Keep it short."


def session_day_context() -> str:
    """Returns short context based on day of week."""
    weekday = datetime.now().weekday()
    if weekday == 0:
        return "Week start \u2014 good time to set priorities."
    elif weekday == 4:
        return "End of week \u2014 good time to migrate and reflect."
    return ""


def session_greeting(streak: int, pending_count: int) -> str:
    """Full contextual greeting combining time, streak, and pending awareness.

    Args:
        streak: Consecutive days with entries.
        pending_count: Number of pending tasks today.
    """
    hour = datetime.now().hour
    weekday = datetime.now().weekday()

    # Time-of-day base
    if 5 <= hour < 12:
        time_tone = "Morning"
    elif 12 <= hour < 17:
        time_tone = "Afternoon"
    elif 17 <= hour < 22:
        time_tone = "Evening"
    else:
        time_tone = "Late"

    # Build greeting based on time
    if 5 <= hour < 12:
        if pending_count > 0:
            msg = f"{time_tone}. {pending_count} task{'s' if pending_count != 1 else ''} waiting. Let's move."
        else:
            msg = f"{time_tone}. Clear slate. Set your priorities."
    elif 12 <= hour < 17:
        msg = f"{time_tone}. Keep the thread."
    elif 17 <= hour < 22:
        msg = f"{time_tone}. Good time to migrate and note what landed."
    else:
        msg = f"{time_tone}. Capture what's in your head. Sleep wins."

    # Streak acknowledgment
    if streak >= 3:
        msg += f"  ({streak}-day streak)"

    # Day-of-week context
    if weekday == 0:
        msg += "  Set your 3 priorities."
    elif weekday == 4:
        msg += "  Migrate before the weekend."

    # Pending flag (if high)
    if pending_count > 7 and weekday != 4:
        msg = msg.replace(
            "Keep the thread.",
            f"Keep the thread. ({pending_count} pending \u2014 time to triage?)",
        )

    return msg
