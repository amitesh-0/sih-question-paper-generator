import sys
from fastapi.testclient import TestClient
import psycopg2
from main import app

client = TestClient(app)

try:
    conn = psycopg2.connect(
        dbname="sih_exam_db",
        user="admin",
        password="password123",
        host="127.0.0.1",
        port="5433"
    )
    cursor = conn.cursor()
    # Insert dummy blueprint if not exists
    cursor.execute("""
        INSERT INTO paper_blueprints (blueprint_id, course_id, syllabus_id, exam_type_id, total_marks, duration_minutes, created_by)
        VALUES (1, 1, 1, 1, 100, 180, 1)
        ON CONFLICT DO NOTHING
    """)
    conn.commit()
except Exception as e:
    print(f"Failed to setup dummy blueprint: {e}")

payload = {
    "blueprint_id": 1,
    "triggered_by": 1,
    "set_label": "TEST_A",
    "mark_template": [
        {"marks": 1, "count": 2},
        {"marks": 5, "count": 1}
    ],
    "target_difficulty_avg": 5.0,
    "target_difficulty_spread": 2.0,
    "target_bloom_avg": 3.0,
    "target_bloom_spread": 1.5
}

print("Sending request to generate paper...")
response = client.post("/generate-paper", json=payload)
if response.status_code != 200:
    print("Failed!")
    print(response.json())
    sys.exit(1)

data = response.json()
print("Success!")
print(f"Generated Set ID: {data.get('set_id')}")
print(f"Generation Batch ID: {data.get('generation_batch_id')}")

# Verify in DB
try:
    conn = psycopg2.connect(
        dbname="sih_exam_db",
        user="admin",
        password="password123",
        host="127.0.0.1",
        port="5433"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM paper_sets WHERE set_id = %s", (data.get('set_id'),))
    result = cursor.fetchone()
    count = result[0] if result else 0
    print(f"Verified paper_sets count: {count}")
    
    cursor.execute("SELECT count(*) FROM set_questions WHERE set_id = %s", (data.get('set_id'),))
    result = cursor.fetchone()
    sq_count = result[0] if result else 0
    print(f"Verified set_questions count: {sq_count} (Expected 3)")
except Exception as e:
    print(f"DB check failed: {e}")
