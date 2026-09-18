"""
streamlit_app.py — Streamlit UI for the CRM Support Ticket AI System.
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="CRM Ticket Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .main { background: #0f1117; }

  /* Hero gradient header */
  .hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    color: white;
  }
  .hero h1 { font-size: 2rem; font-weight: 700; margin: 0; }
  .hero p  { font-size: 1rem; opacity: 0.85; margin: 6px 0 0; }

  /* KPI cards */
  .kpi-card {
    background: linear-gradient(135deg, #1e1e2e, #2a2a3e);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    transition: transform 0.2s;
  }
  .kpi-card:hover { transform: translateY(-3px); }
  .kpi-value { font-size: 2.2rem; font-weight: 700; color: #a78bfa; }
  .kpi-label { font-size: 0.82rem; color: #8b8fa8; text-transform: uppercase; letter-spacing: .05em; margin-top: 4px; }

  /* Anomaly pill */
  .anomaly-pill {
    display: inline-block;
    background: rgba(239,68,68,0.15);
    border: 1px solid rgba(239,68,68,0.4);
    color: #f87171;
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    margin: 2px 2px;
  }

  /* Query result card */
  .answer-box {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border-left: 4px solid #a78bfa;
    border-radius: 8px;
    padding: 18px 22px;
    color: #e2e8f0;
    font-size: 1rem;
    line-height: 1.6;
    margin: 12px 0;
  }

  /* Sidebar */
  section[data-testid="stSidebar"] { background: #13131f; }

  /* Divider */
  .subtle-divider { border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 20px 0; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def api_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "❌ Cannot reach the API. Make sure the backend is running (`run.bat`)."
    except Exception as e:
        return None, f"❌ API error: {e}"


def api_post(path: str, payload: dict):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=60)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "❌ Cannot reach the API. Make sure the backend is running (`run.bat`)."
    except Exception as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, f"❌ {detail}"


def status_color(status: str) -> str:
    return {"Open": "🟡", "Resolved": "🟢", "Escalated": "🔴"}.get(status, "⚪")


def priority_color(priority: str) -> str:
    return {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(priority, "⚪")


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🎯 CRM Intelligence")
    st.markdown("---")

    # Health check
    health, err = api_get("/health")
    if health:
        st.success(f"**API:** Online\n\n**DB rows:** {health['db_rows']}\n\n**Model:** {health['model']}")
    else:
        st.error("API Offline")

    st.markdown("---")
    st.markdown("### Sample Queries")
    sample_queries = [
        "How many tickets are currently open?",
        "Which agent resolved the most tickets?",
        "What is the average customer rating for Technical tickets?",
        "Show me all High priority open tickets",
        "Which agent has the lowest average customer rating?",
        "How many billing tickets were resolved last month?",
        "What are the top 5 longest resolution times?",
    ]
    selected_sample = st.selectbox("Try a sample →", [""] + sample_queries)

    st.markdown("---")
    st.caption("Built with FastAPI + Groq LLaMA-3.3 + Streamlit")

# ── Hero ──────────────────────────────────────────────────────────────────────

st.markdown(
    """
<div class="hero">
  <h1>🎯 CRM Support Ticket Intelligence</h1>
  <p>AI-powered analytics — Ask anything, detect anomalies, explore KPIs</p>
</div>
""",
    unsafe_allow_html=True,
)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(
    ["💬 Natural Language Query", "🚨 Anomaly Detection", "📊 Dashboard", "🗂️ Browse Tickets"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — NL Query
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Ask anything about your support tickets")
    st.markdown(
        "The AI will convert your question into SQL, run it against the database, "
        "and give you a clear answer."
    )

    # Pre-fill from sidebar sample
    default_q = selected_sample if selected_sample else ""

    col_input, col_btn = st.columns([5, 1])
    with col_input:
        question = st.text_input(
            "Your question",
            value=default_q,
            placeholder="e.g. Which agent resolved the most tickets this month?",
            label_visibility="collapsed",
        )
    with col_btn:
        ask_btn = st.button("Ask →", type="primary", use_container_width=True)

    if ask_btn and question.strip():
        with st.spinner("🤖 Thinking …"):
            result, err = api_post("/query", {"question": question})

        if err:
            st.error(err)
        else:
            # Answer box
            st.markdown(
                f'<div class="answer-box">💡 {result["answer"]}</div>',
                unsafe_allow_html=True,
            )

            col_a, col_b = st.columns(2)
            col_a.metric("Rows returned", result["row_count"])
            col_b.metric("Question", f'"{question[:40]}…"' if len(question) > 40 else f'"{question}"')

            with st.expander("🔍 View generated SQL"):
                st.code(result["sql"], language="sql")

            if result["results"]:
                st.markdown(f"**Results Table ({len(result['results'])} rows)**")
                df = pd.DataFrame(result["results"])
                
                # If full ticket table is returned, apply custom column formatting
                if "ticket_id" in df.columns:
                    col_config = {
                        "ticket_id": st.column_config.TextColumn("Ticket ID", width="small"),
                        "created_at": st.column_config.TextColumn("Created At", width="medium"),
                        "category": st.column_config.TextColumn("Category", width="small"),
                        "priority": st.column_config.TextColumn("Priority", width="small"),
                        "status": st.column_config.TextColumn("Status", width="small"),
                        "response_time_hrs": st.column_config.NumberColumn("Response (hrs)", format="%.1f"),
                        "resolution_time_hrs": st.column_config.NumberColumn("Resolution (hrs)", format="%.1f"),
                        "agent_id": st.column_config.TextColumn("Agent", width="small"),
                        "customer_rating": st.column_config.NumberColumn("Rating", format="%.1f"),
                        "issue_summary": st.column_config.TextColumn("Issue Summary", width="large"),
                    }
                    st.dataframe(df, column_config=col_config, use_container_width=True, height=380)
                else:
                    st.dataframe(df, use_container_width=True, height=350)

                # Download button
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=csv_data,
                    file_name="query_results.csv",
                    mime="text/csv",
                )

                # Auto-visualise if grouped / numeric columns present (and not a raw ticket list)
                if "ticket_id" not in df.columns:
                    num_cols = df.select_dtypes("number").columns.tolist()
                    if len(df.columns) >= 2 and num_cols:
                        x_col = df.columns[0]
                        y_col = num_cols[0]
                        if len(df) > 1 and len(df) <= 30:
                            fig = px.bar(
                                df,
                                x=x_col,
                                y=y_col,
                                color_discrete_sequence=["#a78bfa"],
                                template="plotly_dark",
                                title=f"{y_col} by {x_col}",
                            )
                            fig.update_layout(
                                plot_bgcolor="rgba(0,0,0,0)",
                                paper_bgcolor="rgba(0,0,0,0)",
                                font_color="#e2e8f0",
                            )
                            st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Query returned no rows.")

    elif ask_btn:
        st.warning("Please enter a question first.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Anomaly Detection
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 🚨 Anomaly Detection")
    st.markdown(
        "Automatically flags tickets that violate SLA thresholds, "
        "have abnormal resolution times, low ratings, or are escalated."
    )

    if st.button("🔍 Run Anomaly Scan", type="primary"):
        with st.spinner("Scanning for anomalies …"):
            data, err = api_get("/anomalies", {"llm_summary": "true"})

        if err:
            st.error(err)
        else:
            total = data["total_anomalies"]

            # Summary banner
            if total == 0:
                st.success("✅ No anomalies detected!")
            else:
                st.error(f"⚠️ **{total} anomalous tickets detected**")

                # LLM summary
                if data.get("summary"):
                    st.markdown("#### 🤖 AI Summary")
                    st.markdown(
                        f'<div class="answer-box">{data["summary"]}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown(f"#### Flagged Tickets ({total})")

                for ticket in data["anomalies"]:
                    with st.expander(
                        f"{priority_color(ticket['priority'])} {ticket['ticket_id']} — "
                        f"{ticket['issue_summary']} "
                        f"({status_color(ticket['status'])} {ticket['status']})",
                        expanded=False,
                    ):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Category", ticket["category"])
                        c2.metric("Priority", ticket["priority"])
                        c3.metric("Agent", ticket["agent_id"])
                        c4.metric("Rating", ticket.get("customer_rating") or "N/A")

                        st.markdown("**⚠️ Anomaly reasons:**")
                        reasons_html = " ".join(
                            f'<span class="anomaly-pill">{r}</span>'
                            for r in ticket["anomaly_reasons"]
                        )
                        st.markdown(reasons_html, unsafe_allow_html=True)

                        cols = st.columns(3)
                        cols[0].caption(f"Created: {ticket.get('created_at', 'N/A')}")
                        cols[1].caption(f"Response: {ticket.get('response_time_hrs', 'N/A')}h")
                        cols[2].caption(f"Resolution: {ticket.get('resolution_time_hrs', 'N/A')}h")
    else:
        st.info("Click **Run Anomaly Scan** to detect problematic tickets.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Dashboard
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📊 KPI Dashboard")

    stats, err = api_get("/stats")

    if err:
        st.error(err)
    elif stats:
        # ── KPI row ──────────────────────────────────────────────────────────
        k1, k2, k3, k4, k5 = st.columns(5)
        kpis = [
            (k1, stats.get("total_tickets", 0), "Total Tickets"),
            (k2, stats.get("open_tickets", 0), "Open"),
            (k3, stats.get("resolved_tickets", 0), "Resolved"),
            (k4, stats.get("escalated_tickets", 0), "Escalated"),
            (k5, stats.get("avg_customer_rating", "N/A"), "Avg Rating"),
        ]
        for col, val, label in kpis:
            col.markdown(
                f'<div class="kpi-card">'
                f'<div class="kpi-value">{val}</div>'
                f'<div class="kpi-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<hr class='subtle-divider'>", unsafe_allow_html=True)

        # ── Row 2: charts ─────────────────────────────────────────────────────
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            if stats.get("by_status"):
                df_status = pd.DataFrame(stats["by_status"])
                fig = px.pie(
                    df_status,
                    names="status",
                    values="count",
                    color_discrete_sequence=["#f59e0b", "#10b981", "#ef4444"],
                    title="Tickets by Status",
                    hole=0.5,
                    template="plotly_dark",
                )
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0")
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            if stats.get("by_category"):
                df_cat = pd.DataFrame(stats["by_category"])
                fig = px.bar(
                    df_cat,
                    x="category",
                    y="count",
                    color="category",
                    color_discrete_sequence=["#a78bfa", "#60a5fa", "#34d399"],
                    title="Tickets by Category",
                    template="plotly_dark",
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e2e8f0",
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

        with col_c:
            if stats.get("by_priority"):
                df_pri = pd.DataFrame(stats["by_priority"])
                colors = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"}
                fig = px.bar(
                    df_pri,
                    x="priority",
                    y="count",
                    color="priority",
                    color_discrete_map=colors,
                    title="Tickets by Priority",
                    template="plotly_dark",
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e2e8f0",
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("<hr class='subtle-divider'>", unsafe_allow_html=True)

        # ── Row 3: agents ─────────────────────────────────────────────────────
        col_d, col_e = st.columns(2)

        with col_d:
            if stats.get("top_agents"):
                df_agents = pd.DataFrame(stats["top_agents"])
                fig = px.bar(
                    df_agents,
                    x="agent_id",
                    y="resolved_count",
                    color="avg_rating",
                    color_continuous_scale="Viridis",
                    title="Top Agents by Resolved Tickets",
                    template="plotly_dark",
                    labels={"resolved_count": "Resolved", "avg_rating": "Avg Rating"},
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e2e8f0",
                )
                st.plotly_chart(fig, use_container_width=True)

        with col_e:
            if stats.get("resolution_by_category"):
                df_res = pd.DataFrame(stats["resolution_by_category"])
                fig = px.bar(
                    df_res,
                    x="category",
                    y="avg_resolution_hrs",
                    color="category",
                    color_discrete_sequence=["#a78bfa", "#60a5fa", "#34d399"],
                    title="Avg Resolution Time by Category (hours)",
                    template="plotly_dark",
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e2e8f0",
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

        # ── Performance metrics ───────────────────────────────────────────────
        st.markdown("#### ⏱️ Performance Metrics")
        pm1, pm2 = st.columns(2)
        pm1.metric(
            "Avg Response Time",
            f"{stats.get('avg_response_hrs', 'N/A')} hrs",
            help="Average hours until first agent response",
        )
        pm2.metric(
            "Avg Resolution Time",
            f"{stats.get('avg_resolution_hrs', 'N/A')} hrs",
            help="Average hours from ticket creation to resolution",
        )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Browse Tickets
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 🗂️ Browse & Filter Tickets")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        f_category = st.selectbox("Category", ["All", "General", "Billing", "Technical"])
    with col_f2:
        f_priority = st.selectbox("Priority", ["All", "High", "Medium", "Low"])
    with col_f3:
        f_status = st.selectbox("Status", ["All", "Open", "Resolved", "Escalated"])
    with col_f4:
        f_limit = st.number_input("Rows per page", min_value=10, max_value=200, value=50, step=10)

    params = {"limit": f_limit, "offset": 0}
    if f_category != "All":
        params["category"] = f_category
    if f_priority != "All":
        params["priority"] = f_priority
    if f_status != "All":
        params["status"] = f_status

    data, err = api_get("/tickets", params)
    if err:
        st.error(err)
    elif data:
        st.caption(f"Showing {len(data['tickets'])} of {data['total']} tickets")
        df = pd.DataFrame(data["tickets"])
        if not df.empty:
            # Colour-code status column
            st.dataframe(
                df,
                use_container_width=True,
                height=500,
                column_config={
                    "ticket_id": st.column_config.TextColumn("Ticket ID"),
                    "created_at": st.column_config.TextColumn("Created At"),
                    "category": st.column_config.TextColumn("Category"),
                    "priority": st.column_config.TextColumn("Priority"),
                    "status": st.column_config.TextColumn("Status"),
                    "response_time_hrs": st.column_config.NumberColumn("Response (hrs)", format="%.1f"),
                    "resolution_time_hrs": st.column_config.NumberColumn("Resolution (hrs)", format="%.1f"),
                    "agent_id": st.column_config.TextColumn("Agent"),
                    "customer_rating": st.column_config.NumberColumn("Rating", format="%.1f"),
                    "issue_summary": st.column_config.TextColumn("Issue Summary", width="large"),
                },
            )
        else:
            st.info("No tickets match the selected filters.")
