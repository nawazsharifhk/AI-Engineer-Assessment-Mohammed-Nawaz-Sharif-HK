"""
smoke_test.py -- Quick validation that the DB ingestion and anomaly detection work.
Run without a Groq API key to validate the data pipeline.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import ingest_csv, execute_query, get_summary_stats
from app.anomaly import detect_anomalies

print("=" * 50)
print("Smoke Test -- CRM AI System")
print("=" * 50)

print("\n[1] Ingesting CSV...")
ingest_csv()

print("\n[2] Checking row count...")
rows = execute_query("SELECT COUNT(*) as n FROM tickets")
print(f"    [OK] Total rows: {rows[0]['n']}")

print("\n[3] Sample query -- open tickets by category...")
result = execute_query("""
    SELECT category, COUNT(*) as count
    FROM tickets WHERE status='Open'
    GROUP BY category ORDER BY count DESC
""")
for r in result:
    print(f"    {r['category']}: {r['count']}")

print("\n[4] Stats summary...")
stats = get_summary_stats()
print(f"    Total: {stats['total_tickets']}, Open: {stats['open_tickets']}, "
      f"Resolved: {stats['resolved_tickets']}, Escalated: {stats['escalated_tickets']}")
print(f"    Avg Rating: {stats['avg_customer_rating']}/5")
print(f"    Avg Resolution: {stats['avg_resolution_hrs']}h")

print("\n[5] Anomaly detection...")
anomalies = detect_anomalies()
print(f"    [OK] Flagged {len(anomalies)} anomalous tickets")
if anomalies:
    print(f"    Top anomaly: {anomalies[0]['ticket_id']} -- {anomalies[0]['anomaly_reasons'][0]}")

print("\n[PASS] All checks passed! Backend data pipeline is healthy.")
print("Next step: add your GROQ_API_KEY to .env and run run.bat")
