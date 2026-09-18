"""
anomaly.py — Rule-based anomaly detection for support tickets.
"""
from datetime import datetime, timezone
from typing import Any
from app.database import execute_query


def _age_hours(created_at_str: str) -> float:
    """Return how many hours ago the ticket was created."""
    try:
        dt = datetime.fromisoformat(created_at_str)
        now = datetime.now()
        return (now - dt).total_seconds() / 3600
    except Exception:
        return 0.0


def detect_anomalies() -> list[dict[str, Any]]:
    """
    Apply rule-based anomaly detection. Returns a list of ticket dicts
    with an extra 'anomaly_reasons' list field.
    """
    # Fetch all tickets
    rows = execute_query("""
        SELECT ticket_id, created_at, category, priority, status,
               response_time_hrs, resolution_time_hrs, agent_id,
               customer_rating, issue_summary
        FROM tickets
    """)

    # Compute category average resolution times for relative comparisons
    cat_avg = {}
    cat_rows = execute_query("""
        SELECT category, AVG(resolution_time_hrs) as avg_res
        FROM tickets
        WHERE resolution_time_hrs IS NOT NULL
        GROUP BY category
    """)
    for r in cat_rows:
        cat_avg[r["category"]] = r["avg_res"] or 0

    flagged: list[dict[str, Any]] = []

    for row in rows:
        reasons: list[str] = []
        row = dict(row)

        status = row.get("status", "")
        priority = row.get("priority", "")
        resolution_hrs = row.get("resolution_time_hrs")
        response_hrs = row.get("response_time_hrs")
        rating = row.get("customer_rating")
        category = row.get("category", "")
        created_at = row.get("created_at", "")
        age_hrs = _age_hours(str(created_at)) if created_at else 0

        # Rule 1: High-priority ticket open > 24 hours
        if priority == "High" and status == "Open" and age_hrs > 24:
            reasons.append(
                f"High-priority ticket has been open for {age_hrs:.0f}h (>24h threshold)"
            )

        # Rule 2: Any ticket (not resolved) open > 72 hours
        if status == "Open" and age_hrs > 72:
            reasons.append(
                f"Ticket unresolved for {age_hrs:.0f}h (>72h threshold)"
            )

        # Rule 3: Escalated tickets
        if status == "Escalated":
            reasons.append("Ticket has been escalated and requires immediate attention")

        # Rule 4: Resolution time > 3× category average
        if resolution_hrs is not None and category in cat_avg and cat_avg[category] > 0:
            threshold = cat_avg[category] * 3
            if resolution_hrs > threshold:
                reasons.append(
                    f"Resolution time {resolution_hrs:.1f}h is {resolution_hrs/cat_avg[category]:.1f}× "
                    f"the {category} average ({cat_avg[category]:.1f}h)"
                )

        # Rule 5: Low customer rating (≤ 2) with High priority
        if rating is not None and rating <= 2 and priority == "High":
            reasons.append(
                f"Customer rated only {rating}/5 on a High-priority ticket"
            )

        # Rule 6: Low customer rating (≤ 2) on any resolved ticket
        if rating is not None and rating <= 2 and status == "Resolved":
            if not any("Customer rated" in r for r in reasons):
                reasons.append(f"Low customer satisfaction rating: {rating}/5")

        # Rule 7: Very slow initial response (> 4.5 hrs)
        if response_hrs is not None and response_hrs > 4.5 and priority in ("High", "Medium"):
            reasons.append(
                f"Slow first response: {response_hrs:.1f}h for a {priority}-priority ticket"
            )

        if reasons:
            row["anomaly_reasons"] = reasons
            flagged.append(row)

    # Sort: Escalated first, then High-priority, then by age
    priority_order = {"Escalated": 0, "High": 1, "Medium": 2, "Low": 3}
    flagged.sort(
        key=lambda r: (
            0 if r.get("status") == "Escalated" else 1,
            priority_order.get(r.get("priority", "Low"), 3),
            -_age_hours(str(r.get("created_at", ""))),
        )
    )
    return flagged
