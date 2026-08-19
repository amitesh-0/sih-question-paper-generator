import os
import psycopg2
from fastapi import HTTPException

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "sih_exam_db"),
            user=os.getenv("DB_USER", "admin"),
            password=os.getenv("DB_PASSWORD", "password123"),
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=os.getenv("DB_PORT", "5433")
        )
        return conn
    except Exception as e:
        print(f"Connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
