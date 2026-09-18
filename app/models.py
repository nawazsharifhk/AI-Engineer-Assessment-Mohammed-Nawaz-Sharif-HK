"""
models.py — Pydantic request / response models.
"""
from pydantic import BaseModel
from typing import Any, Optional


class QueryRequest(BaseModel):
    question: str
    max_rows: int = 500


class QueryResponse(BaseModel):
    question: str
    sql: str
    results: list[dict[str, Any]]
    answer: str
    row_count: int


class AnomalyTicket(BaseModel):
    ticket_id: str
    category: str
    priority: str
    status: str
    agent_id: str
    issue_summary: str
    created_at: Optional[str]
    resolution_time_hrs: Optional[float]
    response_time_hrs: Optional[float]
    customer_rating: Optional[float]
    anomaly_reasons: list[str]


class AnomalyResponse(BaseModel):
    total_anomalies: int
    anomalies: list[AnomalyTicket]
    summary: str


class HealthResponse(BaseModel):
    status: str
    db_rows: int
    model: str
    version: str


class TicketFilter(BaseModel):
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    agent_id: Optional[str] = None
    limit: int = 50
    offset: int = 0
