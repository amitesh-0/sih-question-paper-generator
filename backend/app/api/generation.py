from fastapi import APIRouter, HTTPException
from psycopg2.extras import RealDictCursor
from typing import List

from app.db.database import get_db_connection
from app.schemas.generation import GenerationRequest, GenerationResponse, Question
from app.optimizer.solver import run_milp_solver

router = APIRouter()

def map_expected_answer_length(length_str: str) -> float:
    mapping = {
        'One-Word': 1.0,
        'One-Sentence': 2.0,
        'Short-Paragraph': 4.0,
        'Multi-Paragraph': 6.0,
        'Essay/Derivation': 10.0,
        'Diagram-Only': 5.0
    }
    return mapping.get(length_str, 5.0)

@router.post("/generate-paper", response_model=GenerationResponse)
def generate_paper(request: GenerationRequest):
    # 1. Fetch questions from the database
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT 
            q.question_id, 
            qt.default_marks as marks, 
            q.bloom_id, 
            q.difficulty_id, 
            q.expected_answer_length
        FROM questions q
        JOIN question_types qt ON q.question_type_id = qt.question_type_id
        WHERE q.status = 'Draft'
    """
    params = []
    
    if request.topic_id is not None:
        query += " AND q.topic_id = %s"
        params.append(request.topic_id)
        
    try:
        cursor.execute(query, tuple(params))
        db_questions = cursor.fetchall()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")
    finally:
        cursor.close()
        conn.close()

    if not db_questions:
        raise HTTPException(status_code=400, detail="No candidate questions found in the database. Add some questions to generate a paper.")

    questions: List[Question] = []
    diff_map = {1: 3.3, 2: 6.6, 3: 10.0}
    for row in db_questions:
        questions.append(Question(
            id=str(row['question_id']),
            bloom_level=row['bloom_id'],
            difficulty_level=diff_map.get(row['difficulty_id'], 5.0),
            answer_length=map_expected_answer_length(row['expected_answer_length'])
        ))

    print(f"Fetched {len(questions)} questions for the optimizer.")

    # 2. Run the optimizer
    status_str, selected, achieved_marks, total_qs, avg_diff, spread_diff, avg_bloom, spread_bloom = run_milp_solver(questions, request)

    if status_str in ["OPTIMAL", "FEASIBLE"]:
        # 3. Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO generation_batches (blueprint_id, triggered_by, model_used, requested_set_count, status)
                VALUES (%s, %s, %s, %s, %s) RETURNING generation_batch_id
            """, (request.blueprint_id, request.triggered_by, 'OR-Tools MILP Solver', 1, 'Completed'))
            result = cursor.fetchone()
            if not result:
                raise Exception("Failed to retrieve generation_batch_id after insert.")
            generation_batch_id = result[0]

            cursor.execute("""
                INSERT INTO paper_sets (blueprint_id, generation_batch_id, set_label, confidentiality_classification, status)
                VALUES (%s, %s, %s, %s, %s) RETURNING set_id
            """, (request.blueprint_id, generation_batch_id, request.set_label, 'Restricted', 'Generated'))
            result = cursor.fetchone()
            if not result:
                raise Exception("Failed to retrieve set_id after insert.")
            set_id = result[0]

            sequence_no = 1
            for sq in selected:
                cursor.execute("""
                    INSERT INTO set_questions (set_id, question_id, sequence_no, marks_allotted)
                    VALUES (%s, %s, %s, %s)
                """, (set_id, int(sq.id), sequence_no, sq.assigned_marks))
                sequence_no += 1

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save paper to database: {e}")
        finally:
            cursor.close()
            conn.close()

        return GenerationResponse(
            status=status_str,
            generation_batch_id=generation_batch_id,
            set_id=set_id,
            total_marks=achieved_marks,
            total_questions=total_qs,
            actual_difficulty_avg=avg_diff,
            actual_difficulty_spread=spread_diff,
            actual_bloom_avg=avg_bloom,
            actual_bloom_spread=spread_bloom,
            selected_questions=selected
        )
    else:
        raise HTTPException(status_code=422, detail="No feasible paper could be generated. Try expanding your question pool.")
