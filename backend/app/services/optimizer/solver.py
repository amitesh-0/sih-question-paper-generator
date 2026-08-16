from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from ortools.linear_solver import pywraplp

app = FastAPI(title="Strict MILP Generator: 3-Factor Marks & Bloom Targets")

# --- Pydantic Data Models ---

class Question(BaseModel):
    id: str
    bloom_level: int = Field(..., ge=1, le=6)
    difficulty_level: float = Field(..., ge=1.0, le=10.0)
    answer_length: float = Field(..., ge=1.0, le=10.0, description="1 (One word) to 10 (Multi-page essay)")

class MarkTemplate(BaseModel):
    marks: int
    count: int

class GenerationRequest(BaseModel):
    questions: List[Question]
    
    # 1. The Strict Blueprint (Hard Constraints)
    mark_template: List[MarkTemplate]
    
    # 2. Difficulty Targets (Soft Constraints)
    target_difficulty_avg: float      
    target_difficulty_spread: float          
    
    # 3. Bloom's Targets (Soft Constraints)
    target_bloom_avg: float
    target_bloom_spread: float

    # 4. The Trade-off Knobs (Weights)
    weight_diff_avg: float = 2.0
    weight_diff_spread: float = 1.5           
    weight_bloom_avg: float = 2.0
    weight_bloom_spread: float = 1.5
    weight_mark_alignment: float = 3.0  # Penalty for mismatching the 3-Factor expected mark

class GeneratedQuestion(BaseModel):
    id: str
    assigned_marks: int
    bloom_level: int
    difficulty_level: float
    answer_length: float

class GenerationResponse(BaseModel):
    status: str
    total_marks: int
    total_questions: int
    actual_difficulty_avg: float
    actual_difficulty_spread: float
    actual_bloom_avg: float
    actual_bloom_spread: float                 
    selected_questions: List[GeneratedQuestion]

# --- Solver Logic ---

@app.post("/generate-paper", response_model=GenerationResponse)
def generate_paper(request: GenerationRequest):
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        raise HTTPException(status_code=500, detail="Solver not initialized.")

    # Auto-calculate derived hard constraints from the user's template
    allowed_marks = list(set([tmpl.marks for tmpl in request.mark_template]))
    target_total_questions = sum(tmpl.count for tmpl in request.mark_template)
    target_total_marks = sum(tmpl.marks * tmpl.count for tmpl in request.mark_template)
    max_template_mark = max(allowed_marks) if allowed_marks else 10

    # 1. Decision Variables
    x = {}
    for q in request.questions:
        for m in allowed_marks:
            x[(q.id, m)] = solver.IntVar(0, 1, f'x_{q.id}_{m}')

    # ==========================================
    # 2. HARD CONSTRAINTS (ABSOLUTE RULES)
    # ==========================================
    
    # A question can only be picked once (and assigned one specific mark)
    for q in request.questions:
        solver.Add(sum(x[(q.id, m)] for m in allowed_marks) <= 1)

    # EXACT Mark Template Compliance (Must exactly match user requests)
    # If user wants four 5-mark questions, they get exactly four.
    for tmpl in request.mark_template:
        solver.Add(sum(x[(q.id, tmpl.marks)] for q in request.questions) == tmpl.count)

    # ==========================================
    # 3. SOFT CONSTRAINTS (THE ALIGNMENT)
    # ==========================================
    objective_terms = []

    # A. Difficulty Average & Spread
    d_avg_target = request.target_difficulty_avg * target_total_questions
    d_avg_actual = sum(q.difficulty_level * x[(q.id, m)] for q in request.questions for m in allowed_marks)
    d_plus, d_minus = solver.NumVar(0, solver.infinity(), 'dp'), solver.NumVar(0, solver.infinity(), 'dm')
    solver.Add(d_avg_actual - d_plus + d_minus == d_avg_target)
    objective_terms.append(request.weight_diff_avg * (d_plus + d_minus))

    d_spread_target = request.target_difficulty_spread * target_total_questions
    d_spread_actual = sum(abs(q.difficulty_level - request.target_difficulty_avg) * x[(q.id, m)] for q in request.questions for m in allowed_marks)
    ds_plus, ds_minus = solver.NumVar(0, solver.infinity(), 'dsp'), solver.NumVar(0, solver.infinity(), 'dsm')
    solver.Add(d_spread_actual - ds_plus + ds_minus == d_spread_target)
    objective_terms.append(request.weight_diff_spread * (ds_plus + ds_minus))

    # B. Bloom's Average & Spread
    b_avg_target = request.target_bloom_avg * target_total_questions
    b_avg_actual = sum(q.bloom_level * x[(q.id, m)] for q in request.questions for m in allowed_marks)
    b_plus, b_minus = solver.NumVar(0, solver.infinity(), 'bp'), solver.NumVar(0, solver.infinity(), 'bm')
    solver.Add(b_avg_actual - b_plus + b_minus == b_avg_target)
    objective_terms.append(request.weight_bloom_avg * (b_plus + b_minus))

    b_spread_target = request.target_bloom_spread * target_total_questions
    b_spread_actual = sum(abs(q.bloom_level - request.target_bloom_avg) * x[(q.id, m)] for q in request.questions for m in allowed_marks)
    bs_plus, bs_minus = solver.NumVar(0, solver.infinity(), 'bsp'), solver.NumVar(0, solver.infinity(), 'bsm')
    solver.Add(b_spread_actual - bs_plus + bs_minus == b_spread_target)
    objective_terms.append(request.weight_bloom_spread * (bs_plus + bs_minus))

    # C. The 3-Factor Mark Alignment (Dynamic Resizing)
    for q in request.questions:
        # Calculate how "big" the question is based on the 3 factors (Normalized to 0-1)
        # Assuming equal weight to all three. You can adjust the /3 logic if one is more important.
        intrinsic_size = ( (q.bloom_level/6) + (q.difficulty_level/10) + (q.answer_length/10) ) / 3
        
        # Scale the size to the maximum mark available in the current template
        ideal_mark = intrinsic_size * max_template_mark

        for m in allowed_marks:
            # How far is the assigned mark from what the question intrinsically deserves?
            alignment_penalty = abs(m - ideal_mark)
            objective_terms.append(request.weight_mark_alignment * alignment_penalty * x[(q.id, m)])

    # ==========================================
    # 4. SOLVE
    # ==========================================
    solver.Minimize(solver.Sum(objective_terms))
    status = solver.Solve()

    if status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        selected = []
        achieved_marks, total_qs, total_diff, total_diff_spread, total_bloom, total_bloom_spread = 0, 0, 0, 0, 0, 0

        for q in request.questions:
            for m in allowed_marks:
                if x[(q.id, m)].solution_value() > 0.5:
                    selected.append(GeneratedQuestion(
                        id=q.id, assigned_marks=m, bloom_level=q.bloom_level, difficulty_level=q.difficulty_level, answer_length=q.answer_length
                    ))
                    achieved_marks += m
                    total_qs += 1
                    total_diff += q.difficulty_level
                    total_diff_spread += abs(q.difficulty_level - request.target_difficulty_avg)
                    total_bloom += q.bloom_level
                    total_bloom_spread += abs(q.bloom_level - request.target_bloom_avg)

        return GenerationResponse(
            status="OPTIMAL" if status == pywraplp.Solver.OPTIMAL else "FEASIBLE",
            total_marks=achieved_marks,
            total_questions=total_qs,
            actual_difficulty_avg=total_diff / total_qs if total_qs > 0 else 0,
            actual_difficulty_spread=total_diff_spread / total_qs if total_qs > 0 else 0,
            actual_bloom_avg=total_bloom / total_qs if total_qs > 0 else 0,
            actual_bloom_spread=total_bloom_spread / total_qs if total_qs > 0 else 0,
            selected_questions=selected
        )
    else:
        raise HTTPException(status_code=422, detail="No feasible paper could be generated. Try expanding your question pool.")