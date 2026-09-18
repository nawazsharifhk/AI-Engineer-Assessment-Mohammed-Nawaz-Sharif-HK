# 🎯 CRM Support Ticket AI System

An AI-powered analytics system for customer support ticket data. Built for the **DOTMappers AI Engineer Assessment**.

---

## 🏗️ Architecture

```
support_tickets.csv
        ↓
  [CSV Ingestor] ──▶ SQLite (tickets.db)
        ↓
  [FastAPI Backend]  (port 8000)
    ├── /health        → System health check
    ├── /query         → NL question → Groq LLaMA-3.3 → SQL → Answer
    ├── /anomalies     → Rule-based anomaly detection + LLM summary
    ├── /stats         → Aggregate KPIs and breakdowns
    └── /tickets       → Paginated, filterable ticket listing
        ↓
  [Streamlit UI]  (port 8501)
    ├── 💬 Natural Language Query tab
    ├── 🚨 Anomaly Detection tab
    ├── 📊 KPI Dashboard tab
    └── 🗂️ Browse Tickets tab
```

**Key design decisions:**
- **SQLite**: Zero-config, zero-cost, file-based — perfect for a 500-row dataset. In production, swap for PostgreSQL.
- **Groq free tier** (`llama-3.3-70b-versatile`): Fast (≈1s), free, no local GPU. Falls back gracefully if LLM fails.
- **Two-stage LLM pipeline**: NL → SQL (temp=0, deterministic) + SQL results → Human answer (temp=0.3).
- **Rule-based anomaly detection**: 7 deterministic rules guarantee anomaly coverage even if the LLM is unavailable.

---

## 🚀 Setup & Run

### Prerequisites
- Python 3.11+
- A **free** Groq API key → [console.groq.com](https://console.groq.com) (sign up takes 30 seconds)

### 1. Clone / Navigate to Project

```bash
cd "AI Intern - Assessment"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Key

```bash
# Copy the template
copy .env.example .env        # Windows
cp .env.example .env          # Linux/Mac

# Edit .env and paste your Groq API key
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. Start the System (single command)

**Windows:**
```bat
run.bat
```

**Linux / Mac:**
```bash
bash run.sh
```

This launches:
- **FastAPI backend** → http://localhost:8000
- **Interactive API docs** → http://localhost:8000/docs
- **Streamlit UI** → http://localhost:8501

---

## 📡 REST API Reference

### `GET /health`
Health check. Confirms API is running and database is populated.

**Response:**
```json
{
  "status": "ok",
  "db_rows": 500,
  "model": "llama-3.3-70b-versatile (Groq)",
  "version": "1.0.0"
}
```

---

### `POST /query`
Submit a natural language question. Returns SQL, raw results, and a human-readable answer.

**Request:**
```json
{
  "question": "Which agent resolved the most tickets?",
  "max_rows": 100
}
```

**Response:**
```json
{
  "question": "Which agent resolved the most tickets?",
  "sql": "SELECT agent_id, COUNT(*) as resolved_count FROM tickets WHERE status='Resolved' GROUP BY agent_id ORDER BY resolved_count DESC LIMIT 1",
  "results": [{ "agent_id": "AGT-03", "resolved_count": 52 }],
  "answer": "AGT-03 resolved the most tickets with 52 resolved tickets.",
  "row_count": 1
}
```

---

### `GET /anomalies?llm_summary=true`
Run anomaly detection across all tickets. Returns flagged tickets with reasons + an LLM-generated executive summary.

**Response:**
```json
{
  "total_anomalies": 47,
  "anomalies": [
    {
      "ticket_id": "TKT-025",
      "category": "Billing",
      "priority": "Low",
      "status": "Escalated",
      "agent_id": "AGT-09",
      "issue_summary": "Refund not processed",
      "created_at": "2024-03-02 16:58",
      "resolution_time_hrs": null,
      "response_time_hrs": 1.0,
      "customer_rating": null,
      "anomaly_reasons": ["Ticket has been escalated and requires immediate attention"]
    }
  ],
  "summary": "• 12 escalated tickets require immediate attention ..."
}
```

---

### `GET /stats`
Returns KPI dashboard data: counts, averages, breakdowns by category/priority/status, agent leaderboard.

---

### `GET /tickets?category=Billing&priority=High&status=Open&limit=50`
Paginated ticket listing with optional filters.

---

## 🔍 Example Queries

| Question | Answer |
|----------|--------|
| "How many tickets are currently open?" | "There are 127 tickets currently open." |
| "Which agent resolved the most tickets?" | "AGT-03 resolved the most tickets with 52 resolved." |
| "What is the average customer rating for Technical tickets?" | "The average rating is 3.4/5 for Technical category tickets." |
| "Show all High priority open tickets" | Returns table of High+Open tickets |
| "What is the average resolution time for Billing tickets?" | "The average resolution time for Billing tickets is 18.3 hours." |
| "Which agent has the lowest average customer rating?" | "AGT-11 has the lowest average rating of 2.8/5." |

---

## 🚨 Anomaly Detection Rules

The system applies **7 rule-based checks**:

| # | Rule | Threshold |
|---|------|-----------|
| 1 | High-priority ticket still open | > 24 hours |
| 2 | Any ticket unresolved | > 72 hours |
| 3 | Ticket escalated | Any escalated status |
| 4 | Abnormally long resolution time | > 3× category average |
| 5 | Low rating on high-priority resolved ticket | Rating ≤ 2 AND priority = High |
| 6 | Low rating on any resolved ticket | Rating ≤ 2 |
| 7 | Slow first response on critical tickets | > 4.5h on High/Medium priority |

After detection, the Groq LLM generates a concise executive summary of the most critical issues.

---

## 🛠️ Tools & Technologies

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11 | Required |
| API Framework | FastAPI | Modern, fast, auto-docs |
| Database | SQLite | Zero-config, zero-cost |
| LLM | Groq (llama-3.3-70b) | Free tier, ~1s latency |
| UI | Streamlit | Rapid prototyping |
| Charts | Plotly | Interactive visualisations |
| Data | Pandas | CSV ingestion + processing |

---

## ⚠️ Known Limitations

1. **SQL injection risk**: The NL→SQL pipeline uses the LLM to generate SQL. Input validation is limited to rejecting non-SELECT queries. In production, use parameterized queries and a stricter SQL parser.
2. **SQLite concurrency**: SQLite doesn't handle high write concurrency. For production, use PostgreSQL.
3. **LLM hallucination**: The LLM may occasionally generate invalid SQL for complex multi-step questions. Retry or rephrase the question.
4. **No authentication**: The API has no auth layer. Add OAuth2 / API keys before production deployment.
5. **Static dataset**: The CSV is ingested once at startup. Real-time ingestion would require a message queue (e.g., Kafka).
6. **Cost**: The system uses Groq's free tier which has rate limits (~30 req/min). Under heavy load, queries may be throttled.

---

## 📁 Project Structure

```
AI Intern - Assessment/
├── support_tickets.csv      # Source dataset (500 rows)
├── tickets.db               # Auto-generated SQLite database
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application + all endpoints
│   ├── database.py          # CSV ingestion + SQLite interface
│   ├── llm.py               # Groq LLM integration (NL→SQL, answers, summaries)
│   ├── anomaly.py           # 7-rule anomaly detection engine
│   └── models.py            # Pydantic request/response models
├── ui/
│   └── streamlit_app.py     # Full Streamlit UI (4 tabs)
├── requirements.txt
├── .env.example             # API key template
├── run.bat                  # Windows one-command startup
├── run.sh                   # Linux/Mac one-command startup
└── README.md
```

---

## 📬 Submission

Built by: Mohammed Nawaz Sharif HK  
Assessment: DOTMappers AI Engineer Role  
Email:(mailto:RajathKumar@dotmappers.in)
