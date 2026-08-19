import psycopg2
from faker import Faker
import random
import json

fake = Faker()

def get_db_connection():
    return psycopg2.connect(
        dbname="sih_exam_db",
        user="admin",
        password="password123",
        host="127.0.0.1",
        port="5433"
    )

def fetch_returning_id(cursor, entity_name="row"):
    res = cursor.fetchone()
    if res is None:
        raise RuntimeError(f"Failed to insert {entity_name}. The database returned no rows. "
                           "This usually happens if an ON CONFLICT DO NOTHING clause was used, "
                           "or a trigger/rule prevented the insert.")
    return res[0]

def seed_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("Seeding database...")
    
    # 1. Institutions
    cursor.execute("INSERT INTO institutions (name, university_code) VALUES (%s, %s) RETURNING institution_id",
                   (fake.company() + " University", fake.unique.bothify(text='UNI-####')))
    institution_id = fetch_returning_id(cursor, "institution")

    # 2. Departments
    dept_ids = []
    for _ in range(5):
        cursor.execute("INSERT INTO departments (institution_id, name) VALUES (%s, %s) RETURNING department_id",
                       (institution_id, fake.job() + " Department"))
        dept_ids.append(fetch_returning_id(cursor, "department"))

    # 3. Users
    user_ids = []
    for _ in range(20):
        role_id = random.randint(1, 6)
        dept_id = random.choice(dept_ids)
        cursor.execute("""
            INSERT INTO users (employee_id, name, email, password_hash, department_id, role_id)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING user_id
        """, (fake.unique.bothify(text='EMP-#####'), fake.name(), fake.unique.email(), "hashed_pw", dept_id, role_id))
        user_ids.append(fetch_returning_id(cursor, "user"))

    # 4. Courses
    course_ids = []
    for _ in range(10):
        dept_id = random.choice(dept_ids)
        owner_id = random.choice(user_ids)
        cursor.execute("""
            INSERT INTO courses (department_id, course_code, course_name, semester, course_owner_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING course_id
        """, (dept_id, fake.unique.bothify(text='CS###'), fake.catch_phrase(), random.randint(1, 8), owner_id))
        course_ids.append(fetch_returning_id(cursor, "course"))

    # 5. Syllabus
    syllabus_ids = []
    for course_id in course_ids:
        approved_by = random.choice(user_ids)
        cursor.execute("""
            INSERT INTO syllabus (course_id, academic_year, version, approved_by)
            VALUES (%s, %s, %s, %s) RETURNING syllabus_id
        """, (course_id, "2023-2024", "v1.0", approved_by))
        syllabus_ids.append(fetch_returning_id(cursor, "syllabus"))

    # 6. Syllabus Units
    unit_ids = []
    for syllabus_id in syllabus_ids:
        for unit_num in range(1, 6):
            cursor.execute("""
                INSERT INTO syllabus_units (syllabus_id, unit_name, unit_number, weightage_percent)
                VALUES (%s, %s, %s, %s) RETURNING unit_id
            """, (syllabus_id, fake.bs(), unit_num, 20.0))
            unit_ids.append(fetch_returning_id(cursor, "unit"))

    # 7. Topics
    topic_ids = []
    for unit_id in unit_ids:
        for _ in range(3):
            cursor.execute("""
                INSERT INTO topics (unit_id, topic_name)
                VALUES (%s, %s) RETURNING topic_id
            """, (unit_id, fake.catch_phrase()))
            topic_ids.append(fetch_returning_id(cursor, "topic"))

    # 8. Course Outcomes
    co_ids = []
    for course_id in course_ids:
        for co_num in range(1, 6):
            cursor.execute("""
                INSERT INTO course_outcomes (course_id, co_code, description)
                VALUES (%s, %s, %s) RETURNING co_id
            """, (course_id, f"CO{co_num}", fake.sentence()))
            co_ids.append(fetch_returning_id(cursor, "course outcome"))

    # 9. Questions (Generate 500 questions)
    expected_answer_lengths = ['One-Word', 'One-Sentence', 'Short-Paragraph', 'Multi-Paragraph', 'Essay/Derivation', 'Diagram-Only']
    sources = ['AI-Generated','Faculty-Authored','Bank-Imported']
    statuses = ['Draft','Approved','Rejected','Archived']

    print("Generating 500 questions...")
    for i in range(500):
        topic_id = random.choice(topic_ids)
        co_id = random.choice(co_ids)
        bloom_id = random.randint(1, 6)
        difficulty_id = random.randint(1, 3)
        question_type_id = random.randint(1, 5)
        created_by = random.choice(user_ids)
        
        expected_len = random.choice(expected_answer_lengths)
        source = random.choice(sources)
        status = random.choice(statuses)

        cursor.execute("""
            INSERT INTO questions (
                topic_id, co_id, bloom_id, difficulty_id, question_type_id,
                question_text, expected_answer_length, source, status, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            topic_id, co_id, bloom_id, difficulty_id, question_type_id,
            fake.paragraph() + "?", expected_len, source, status, created_by
        ))
        if i % 100 == 0:
            print(f"  Inserted {i} questions...")

    conn.commit()
    cursor.close()
    conn.close()
    print("\nSUCCESSFULLY SEEDED! Database is now full of dummy data.")

if __name__ == "__main__":
    seed_db()
