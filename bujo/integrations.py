"""Obsidian integration for BuJo."""

import os
from datetime import datetime
from pathlib import Path


def should_add_frontmatter() -> bool:
    """Check if frontmatter is enabled via env var."""
    return os.environ.get("BUJO_OBSIDIAN_FRONTMATTER") == "1"


def should_generate_dashboard() -> bool:
    """Check if dashboard is enabled via env var."""
    return os.environ.get("BUJO_DASHBOARD") == "1"


def add_frontmatter(path: Path, metadata: dict) -> None:
    """Add or update YAML frontmatter in a markdown file.
    Only runs if BUJO_OBSIDIAN_FRONTMATTER=1 is set.
    Never overwrites user-added fields — merges only.
    """
    if not should_add_frontmatter():
        return

    content = path.read_text(encoding="utf-8") if path.exists() else ""

    # Check if frontmatter exists
    if content.startswith("---"):
        # Parse existing frontmatter and merge
        parts = content.split("---", 2)
        if len(parts) >= 3:
            existing_fm = parts[1]
            rest = parts[2]
            # Add new fields that don't exist
            for key, value in metadata.items():
                if f"{key}:" not in existing_fm:
                    existing_fm = existing_fm.rstrip("\n") + f"\n{key}: {value}\n"
            new_content = f"---{existing_fm}---{rest}"
        else:
            # Malformed frontmatter, recreate
            new_content = _create_frontmatter(metadata, content)
    else:
        new_content = _create_frontmatter(metadata, content)

    path.write_text(new_content, encoding="utf-8")


def _create_frontmatter(metadata: dict, content: str) -> str:
    """Create new frontmatter block."""
    fm_lines = ["---"]
    for key, value in metadata.items():
        fm_lines.append(f"{key}: {value}")
    fm_lines.append("---")
    fm_block = "\n".join(fm_lines) + "\n\n"
    return fm_block + content


def generate_dashboard(vault: Path, engine) -> None:
    """Write vault/dashboard.md with current stats.
    Only runs if BUJO_DASHBOARD=1 is set.
    """
    if not should_generate_dashboard():
        return

    report = engine.full_report()
    streak = report["streak"]
    momentum = report["momentum"]
    completion = report["completion_rate_7d"]
    nudge = report["nudge"]

    lines = [
        "# BuJo Dashboard",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Today",
        "",
        f"- **Streak:** {streak} day{'s' if streak != 1 else ''}",
        f"- **Momentum:** {momentum}",
        f"- **7-day completion:** {completion:.0%}",
        "",
    ]

    if report["stuck_tasks"]:
        lines.append("## Stuck Tasks")
        lines.append("")
        for task in report["stuck_tasks"][:5]:
            lines.append(f"- {task['text']} (migrated {task['count']}x)")
        lines.append("")

    if report["kill_themes"]:
        themes = list(report["kill_themes"].items())[:5]
        lines.append("## Kill Themes")
        lines.append("")
        for theme, count in themes:
            lines.append(f"- {theme} ({count}x)")
        lines.append("")

    lines.append("## Today's Nudge")
    lines.append("")
    lines.append(f"> {nudge}")
    lines.append("")

    dashboard = vault / "dashboard.md"
    dashboard.write_text("\n".join(lines), encoding="utf-8")
