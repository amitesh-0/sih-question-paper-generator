import psycopg2

try:
    conn = psycopg2.connect(
        dbname="sih_exam_db",
        user="admin",
        password="password123",
        host="127.0.0.1",
        port="5433"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = [r[0] for r in cursor.fetchall()]
    print("\nSUCCESSFULLY CONNECTED!")
    print(f"Tables found from schema.sql: {tables}\n")
except Exception as e:
    print(f"Real Error: {e}")
