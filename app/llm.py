"""
llm.py — Groq LLM integration for NL → SQL and answer generation.
"""
import os
import re
import json
from groq import Groq
from dotenv import load_dotenv
from app.database import get_schema

load_dotenv()

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    load_dotenv(override=True)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY not set. Add your key to .env file."
        )
    return Groq(api_key=api_key)


MODEL = "openai/gpt-oss-120b"

_NL_TO_SQL_SYSTEM = """You are an expert SQL assistant. Given a SQLite database schema and a natural language question, output ONLY a valid SQLite SELECT query — no markdown, no explanation, no semicolons at the end.

Schema columns: ticket_id, created_at, category, priority, status, response_time_hrs, resolution_time_hrs, agent_id, customer_rating, issue_summary.

CRITICAL RULES:
1. TICKET LISTINGS & COUNTS: When the user asks about tickets or how many/which tickets meet any condition (e.g., "how many tickets are currently open", "show open tickets", "high priority tickets", "tickets unresolved over 12 hours"), ALWAYS return the actual ticket rows using `SELECT * FROM tickets WHERE ...`. 
   DO NOT return `SELECT COUNT(*)` for single-condition ticket queries because the system needs the full ticket rows to populate the UI table while computing the count for the answer.
2. AGGREGATIONS: Use `GROUP BY` and aggregate functions (`AVG`, `COUNT`, `SUM`, `MIN`, `MAX`) only when the question is comparing groups (e.g., "tickets per category", "average rating by agent", "which agent resolved the most tickets").
3. Always use valid SQLite syntax.
4. Never use DROP, INSERT, UPDATE, DELETE.
5. Return ONLY the raw SQL query, nothing else.
"""

_ANSWER_SYSTEM = """You are a helpful data analyst. The user asked a question about a customer support ticket dataset. 
Given the user's question, the SQL query used, the total count of matched rows, and sample results, write a clear, concise, direct human-friendly answer in 1-3 sentences.
State the exact count or answer directly. Do not repeat the SQL query."""


def nl_to_sql(question: str) -> str:
    """Convert a natural language question to a SQLite SQL query."""
    schema = get_schema()
    prompt = f"""Schema:\n{schema}\n\nQuestion: {question}\n\nSQL:"""

    resp = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _NL_TO_SQL_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=512,
    )
    sql = resp.choices[0].message.content.strip()
    # Strip any accidental markdown code fences
    sql = re.sub(r"```sql\s*|```", "", sql, flags=re.IGNORECASE).strip()
    return sql


def generate_answer(question: str, sql: str, results: list[dict]) -> str:
    """Generate a human-readable answer from the query results."""
    preview = results[:50]
    results_json = json.dumps(preview, default=str, indent=2)

    prompt = (
        f"Question: {question}\n\n"
        f"SQL used:\n{sql}\n\n"
        f"Total matching rows returned: {len(results)}\n\n"
        f"Results preview (showing up to 50 of {len(results)} rows):\n{results_json}"
    )

    resp = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _ANSWER_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=300,
    )
    return resp.choices[0].message.content.strip()


def summarise_anomalies(anomalies: list[dict]) -> str:
    """Use LLM to write a brief anomaly report summary."""
    if not anomalies:
        return "No anomalies detected in the current dataset."

    system = (
        "You are a support operations analyst. Summarise the following list of anomalous "
        "customer support tickets in 3-5 concise bullet points, highlighting the most "
        "critical issues that need immediate attention."
    )
    payload = json.dumps(anomalies[:30], default=str, indent=2)
    prompt = f"Anomalous tickets:\n{payload}"

    resp = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=400,
    )
    return resp.choices[0].message.content.strip()
