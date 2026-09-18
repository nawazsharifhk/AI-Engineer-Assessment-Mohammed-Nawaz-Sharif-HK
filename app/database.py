"""
database.py — CSV ingestion and SQLite query interface.
"""
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Any
import os

DB_PATH = Path(__file__).parent.parent / "tickets.db"
CSV_PATH = Path(__file__).parent.parent / "support_tickets.csv"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ingest_csv() -> None:
    """Load support_tickets.csv into SQLite on startup."""
    df = pd.read_csv(CSV_PATH)

    # Normalise column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Ensure numeric types
    df["response_time_hrs"] = pd.to_numeric(df["response_time_hrs"], errors="coerce")
    df["resolution_time_hrs"] = pd.to_numeric(df["resolution_time_hrs"], errors="coerce")
    df["customer_rating"] = pd.to_numeric(df["customer_rating"], errors="coerce")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    conn = get_connection()
    df.to_sql("tickets", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()
    print(f"[DB] Ingested {len(df)} rows into tickets table.")


def execute_query(sql: str) -> list[dict[str, Any]]:
    """Run a SQL query and return rows as list of dicts."""
    conn = get_connection()
    try:
        cur = conn.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
        return rows
    except Exception as e:
        raise ValueError(f"SQL Error: {e}") from e
    finally:
        conn.close()


def get_schema() -> str:
    """Return a compact schema description for the LLM."""
    return """
Table: tickets
Columns:
  - ticket_id       TEXT        e.g. 'TKT-001'
  - created_at      DATETIME    e.g. '2024-02-05 11:14'
  - category        TEXT        one of: 'General', 'Billing', 'Technical'
  - priority        TEXT        one of: 'Low', 'Medium', 'High'
  - status          TEXT        one of: 'Open', 'Resolved', 'Escalated'
  - response_time_hrs   REAL    hours until first response (nullable)
  - resolution_time_hrs REAL    hours until resolution (NULL if not resolved)
  - agent_id        TEXT        e.g. 'AGT-01'
  - customer_rating REAL        1–5 scale (nullable for unresolved)
  - issue_summary   TEXT        short description of the issue
""".strip()


def get_summary_stats() -> dict[str, Any]:
    """Return key aggregate stats for the dashboard."""
    conn = get_connection()
    stats = {}

    queries = {
        "total_tickets": "SELECT COUNT(*) as n FROM tickets",
        "open_tickets": "SELECT COUNT(*) as n FROM tickets WHERE status='Open'",
        "resolved_tickets": "SELECT COUNT(*) as n FROM tickets WHERE status='Resolved'",
        "escalated_tickets": "SELECT COUNT(*) as n FROM tickets WHERE status='Escalated'",
        "avg_resolution_hrs": "SELECT ROUND(AVG(resolution_time_hrs),2) as n FROM tickets WHERE resolution_time_hrs IS NOT NULL",
        "avg_response_hrs": "SELECT ROUND(AVG(response_time_hrs),2) as n FROM tickets WHERE response_time_hrs IS NOT NULL",
        "avg_customer_rating": "SELECT ROUND(AVG(customer_rating),2) as n FROM tickets WHERE customer_rating IS NOT NULL",
    }

    for key, sql in queries.items():
        row = conn.execute(sql).fetchone()
        stats[key] = row["n"] if row else None

    # Category breakdown
    rows = conn.execute(
        "SELECT category, COUNT(*) as count FROM tickets GROUP BY category ORDER BY count DESC"
    ).fetchall()
    stats["by_category"] = [dict(r) for r in rows]

    # Priority breakdown
    rows = conn.execute(
        "SELECT priority, COUNT(*) as count FROM tickets GROUP BY priority ORDER BY count DESC"
    ).fetchall()
    stats["by_priority"] = [dict(r) for r in rows]

    # Status breakdown
    rows = conn.execute(
        "SELECT status, COUNT(*) as count FROM tickets GROUP BY status ORDER BY count DESC"
    ).fetchall()
    stats["by_status"] = [dict(r) for r in rows]

    # Top 5 agents by resolved tickets
    rows = conn.execute("""
        SELECT agent_id, COUNT(*) as resolved_count, ROUND(AVG(customer_rating),2) as avg_rating
        FROM tickets WHERE status='Resolved'
        GROUP BY agent_id ORDER BY resolved_count DESC LIMIT 5
    """).fetchall()
    stats["top_agents"] = [dict(r) for r in rows]

    # Avg resolution by category
    rows = conn.execute("""
        SELECT category, ROUND(AVG(resolution_time_hrs),2) as avg_resolution_hrs
        FROM tickets WHERE resolution_time_hrs IS NOT NULL
        GROUP BY category
    """).fetchall()
    stats["resolution_by_category"] = [dict(r) for r in rows]

    conn.close()
    return stats
