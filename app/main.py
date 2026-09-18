"""
main.py — FastAPI application entry point.

Endpoints:
  GET  /health       → health check
  POST /query        → natural language → SQL → answer
  GET  /anomalies    → detected anomaly tickets
  GET  /stats        → summary KPIs
  GET  /tickets      → paginated ticket listing with optional filters
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import logging

from app.database import ingest_csv, execute_query, get_summary_stats
from app.models import (
    QueryRequest,
    QueryResponse,
    AnomalyResponse,
    AnomalyTicket,
    HealthResponse,
)
from app.llm import nl_to_sql, generate_answer, summarise_anomalies
from app.anomaly import detect_anomalies

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Ingesting CSV into SQLite …")
    ingest_csv()
    logger.info("DB ready.")
    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CRM Support Ticket AI System",
    description=(
        "AI-powered analytics for customer support tickets. "
        "Supports natural language queries, anomaly detection, and KPI dashboards."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Health check — confirms the API is running and the DB is populated."""
    rows = execute_query("SELECT COUNT(*) as n FROM tickets")
    return HealthResponse(
        status="ok",
        db_rows=rows[0]["n"] if rows else 0,
        model="openai/gpt-oss-120b (Groq)",
        version="1.0.0",
    )


@app.post("/query", response_model=QueryResponse, tags=["AI Query"])
def natural_language_query(body: QueryRequest):
    """
    Submit a natural language question about the support ticket data.

    The system will:
    1. Convert the question to SQL using an LLM.
    2. Execute the SQL against the SQLite database.
    3. Generate a human-readable answer using the LLM.
    """
    try:
        sql = nl_to_sql(body.question)
        logger.info(f"Generated SQL: {sql}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    # Safety: only allow SELECT
    if not sql.strip().upper().startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail="LLM produced a non-SELECT query. Only SELECT is permitted.",
        )

    try:
        results = execute_query(sql)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Trim to max_rows
    trimmed = results[: body.max_rows]

    try:
        answer = generate_answer(body.question, sql, trimmed)
    except Exception as e:
        answer = f"(LLM answer generation failed: {e})"

    return QueryResponse(
        question=body.question,
        sql=sql,
        results=trimmed,
        answer=answer,
        row_count=len(results),
    )


@app.get("/anomalies", response_model=AnomalyResponse, tags=["Anomaly Detection"])
def get_anomalies(llm_summary: bool = Query(True, description="Include LLM-generated summary")):
    """
    Detect anomalous tickets using seven rule-based checks:
    - High-priority tickets open > 24 hours
    - Any ticket unresolved > 72 hours
    - Escalated tickets
    - Resolution time > 3× category average
    - Low customer rating (≤ 2) on high-priority tickets
    - Low customer rating (≤ 2) on any resolved ticket
    - Slow first response (> 4.5 h) on High/Medium priority tickets
    """
    flagged = detect_anomalies()

    summary = ""
    if llm_summary and flagged:
        try:
            summary = summarise_anomalies(flagged)
        except Exception as e:
            summary = f"(LLM summary unavailable: {e})"
    elif not flagged:
        summary = "No anomalies detected."

    anomaly_tickets = [
        AnomalyTicket(
            ticket_id=r.get("ticket_id", ""),
            category=r.get("category", ""),
            priority=r.get("priority", ""),
            status=r.get("status", ""),
            agent_id=r.get("agent_id", ""),
            issue_summary=r.get("issue_summary", ""),
            created_at=str(r.get("created_at", "")) if r.get("created_at") else None,
            resolution_time_hrs=r.get("resolution_time_hrs"),
            response_time_hrs=r.get("response_time_hrs"),
            customer_rating=r.get("customer_rating"),
            anomaly_reasons=r.get("anomaly_reasons", []),
        )
        for r in flagged
    ]

    return AnomalyResponse(
        total_anomalies=len(anomaly_tickets),
        anomalies=anomaly_tickets,
        summary=summary,
    )


@app.get("/stats", tags=["Analytics"])
def get_stats():
    """
    Return summary KPIs:
    - Ticket counts (total, open, resolved, escalated)
    - Average response / resolution times
    - Average customer rating
    - Breakdowns by category, priority, status
    - Top 5 agents by resolved count + avg rating
    """
    return get_summary_stats()


@app.get("/tickets", tags=["Data"])
def list_tickets(
    category: Optional[str] = Query(None, description="Filter by category (General/Billing/Technical)"),
    priority: Optional[str] = Query(None, description="Filter by priority (Low/Medium/High)"),
    status: Optional[str] = Query(None, description="Filter by status (Open/Resolved/Escalated)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    List tickets with optional filters and pagination.
    """
    where_clauses = []
    if category:
        where_clauses.append(f"category = '{category}'")
    if priority:
        where_clauses.append(f"priority = '{priority}'")
    if status:
        where_clauses.append(f"status = '{status}'")
    if agent_id:
        where_clauses.append(f"agent_id = '{agent_id}'")

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    count_sql = f"SELECT COUNT(*) as n FROM tickets {where}"
    total = execute_query(count_sql)[0]["n"]

    sql = f"""
        SELECT * FROM tickets {where}
        ORDER BY created_at DESC
        LIMIT {limit} OFFSET {offset}
    """
    rows = execute_query(sql)
    return {"total": total, "limit": limit, "offset": offset, "tickets": rows}
