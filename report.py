import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

import database
from config import Config


# ──────────────────────────────────────────────
#  Text Report Formatting
# ──────────────────────────────────────────────
def _format_number(n: int) -> str:
    """Format large numbers with comma separators."""
    return f"{n:,}"


def _format_tokens(tokens: int) -> str:
    """Format token counts with K/M suffixes."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def _format_bar(value: int, max_value: int, width: int = 20) -> str:
    """Return a simple text bar chart."""
    if max_value == 0:
        return "░" * width
    filled = round(value / max_value * width)
    return "█" * filled + "░" * (width - filled)


def _build_hour_chart(hourly: list[dict[str, Any]]) -> str:
    """Build a compact 24-hour activity chart."""
    hour_map = {h["hour"]: h["message_count"] for h in hourly}
    peak = max(hour_map.values()) if hour_map else 1

    lines = []
    for hour in range(24):
        count = hour_map.get(hour, 0)
        bar = _format_bar(count, peak, width=15)
        label = f"{hour:02d}:00"
        lines.append(f"  {label}  {bar}  {_format_number(count)}")

    return "\n".join(lines)


def generate_text_report() -> str:
    """Generate a formatted text summary report."""
    global_stats = database.get_global_stats()
    top_users = database.get_top_users(limit=10)
    daily = database.get_daily_activity(days=7)
    model_usage = database.get_model_usage()
    hourly = database.get_hourly_distribution()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sections = []

    # ── Header ──
    sections.append(
        f"📊 **BOT ANALYTICS REPORT**\n"
        f"Generated: {now}\n"
        f"{'─' * 40}"
    )

    # ── Global Overview ──
    s = global_stats
    sections.append(
        f"\n🌐 **Global Overview**\n\n"
        f"  Total Users:          {_format_number(s['total_users'])}\n"
        f"  Total Messages:       {_format_number(s['total_messages'])}\n"
        f"  Total Tokens Used:    {_format_tokens(s['total_tokens'])} ({_format_number(s['total_tokens'])})\n"
        f"  Custom Personalities: {_format_number(s['users_with_custom_prompt'])}\n"
        f"  Activity Period:      {s['first_message'] or 'N/A'} → {s['last_message'] or 'N/A'}"
    )

    # ── Top Users ──
    if top_users:
        lines = ["\n👥 **Top Users**\n"]
        for i, u in enumerate(top_users, 1):
            name = u["first_name"] or u["username"] or f"User {u['user_id']}"
            lines.append(
                f"  {i:>2}. {name:<20} "
                f"{_format_number(u['message_count']):>6} msgs  "
                f"{_format_tokens(u['total_tokens']):>8} tokens"
            )
        sections.append("\n".join(lines))
    else:
        sections.append("\n👥 **Top Users**\n\n  No user data yet.")

    # ── Daily Activity (last 7 days) ──
    if daily:
        peak_day = max(d["total_messages"] for d in daily)
        lines = ["\n📅 **Daily Activity (Last 7 Days)**\n"]
        for d in daily:
            bar = _format_bar(d["total_messages"], peak_day, width=15)
            lines.append(
                f"  {d['date']}  {bar}  "
                f"{d['user_messages']}↑ {d['assistant_messages']}↓  "
                f"{_format_tokens(d['total_tokens'])} tok"
            )
        sections.append("\n".join(lines))
    else:
        sections.append("\n📅 **Daily Activity**\n\n  No activity in the last 7 days.")

    # ── Model Usage ──
    if model_usage:
        lines = ["\n🧠 **Model Usage**\n"]
        for m in model_usage:
            lines.append(
                f"  {m['model']:<20} {_format_number(m['message_count']):>6} msgs  "
                f"{_format_tokens(m['total_tokens']):>8} tokens"
            )
        sections.append("\n".join(lines))
    else:
        sections.append("\n🧠 **Model Usage**\n\n  No model usage data yet.")

    # ── Hourly Distribution ──
    if hourly:
        sections.append(
            f"\n⏰ **Hourly Distribution (UTC)**\n\n"
            f"{_build_hour_chart(hourly)}"
        )
    else:
        sections.append("\n⏰ **Hourly Distribution**\n\n  No data yet.")

    return "\n".join(sections)


# ──────────────────────────────────────────────
#  JSON Report
# ──────────────────────────────────────────────
def generate_json_report() -> dict[str, Any]:
    """Generate a structured JSON report with all analytics."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "global": database.get_global_stats(),
        "top_users": database.get_top_users(limit=10),
        "daily_activity": database.get_daily_activity(days=7),
        "model_usage": database.get_model_usage(),
        "hourly_distribution": database.get_hourly_distribution(),
    }


def generate_report_file(export_dir: str | None = None) -> str:
    """Write the JSON report to a file and return the path."""
    data = generate_json_report()

    out_dir = export_dir or tempfile.mkdtemp(prefix="tg_report_")
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filepath = os.path.join(out_dir, f"report_{ts}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath
