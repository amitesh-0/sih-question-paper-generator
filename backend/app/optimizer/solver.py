from ortools.linear_solver import pywraplp
from typing import List, Tuple
from app.schemas.generation import Question, GenerationRequest, GeneratedQuestion

def run_milp_solver(questions: List[Question], request: GenerationRequest) -> Tuple[str, List[GeneratedQuestion], int, int, float, float, float, float]:
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        raise Exception("Solver not initialized.")

    allowed_marks = list(set([tmpl.marks for tmpl in request.mark_template]))
    target_total_questions = sum(tmpl.count for tmpl in request.mark_template)
    target_total_marks = sum(tmpl.marks * tmpl.count for tmpl in request.mark_template)
    max_template_mark = max(allowed_marks) if allowed_marks else 10

    x = {}
    for q in questions:
        for m in allowed_marks:
            x[(q.id, m)] = solver.IntVar(0, 1, f'x_{q.id}_{m}')

    # A question can only be picked once
    for q in questions:
        solver.Add(sum(x[(q.id, m)] for m in allowed_marks) <= 1)

    # EXACT Mark Template Compliance
    for tmpl in request.mark_template:
        solver.Add(sum(x[(q.id, tmpl.marks)] for q in questions) == tmpl.count)

    objective_terms = []

    # Difficulty Average & Spread
    d_avg_target = request.target_difficulty_avg * target_total_questions
    d_avg_actual = sum(q.difficulty_level * x[(q.id, m)] for q in questions for m in allowed_marks)
    d_plus, d_minus = solver.NumVar(0, solver.infinity(), 'dp'), solver.NumVar(0, solver.infinity(), 'dm')
    solver.Add(d_avg_actual - d_plus + d_minus == d_avg_target)
    objective_terms.append(request.weight_diff_avg * (d_plus + d_minus))

    d_spread_target = request.target_difficulty_spread * target_total_questions
    d_spread_actual = sum(abs(q.difficulty_level - request.target_difficulty_avg) * x[(q.id, m)] for q in questions for m in allowed_marks)
    ds_plus, ds_minus = solver.NumVar(0, solver.infinity(), 'dsp'), solver.NumVar(0, solver.infinity(), 'dsm')
    solver.Add(d_spread_actual - ds_plus + ds_minus == d_spread_target)
    objective_terms.append(request.weight_diff_spread * (ds_plus + ds_minus))

    # Bloom's Average & Spread
    b_avg_target = request.target_bloom_avg * target_total_questions
    b_avg_actual = sum(q.bloom_level * x[(q.id, m)] for q in questions for m in allowed_marks)
    b_plus, b_minus = solver.NumVar(0, solver.infinity(), 'bp'), solver.NumVar(0, solver.infinity(), 'bm')
    solver.Add(b_avg_actual - b_plus + b_minus == b_avg_target)
    objective_terms.append(request.weight_bloom_avg * (b_plus + b_minus))

    b_spread_target = request.target_bloom_spread * target_total_questions
    b_spread_actual = sum(abs(q.bloom_level - request.target_bloom_avg) * x[(q.id, m)] for q in questions for m in allowed_marks)
    bs_plus, bs_minus = solver.NumVar(0, solver.infinity(), 'bsp'), solver.NumVar(0, solver.infinity(), 'bsm')
    solver.Add(b_spread_actual - bs_plus + bs_minus == b_spread_target)
    objective_terms.append(request.weight_bloom_spread * (bs_plus + bs_minus))

    # 3-Factor Mark Alignment
    for q in questions:
        intrinsic_size = ( (q.bloom_level/6) + (q.difficulty_level/10) + (q.answer_length/10) ) / 3
        ideal_mark = intrinsic_size * max_template_mark
        for m in allowed_marks:
            alignment_penalty = abs(m - ideal_mark)
            objective_terms.append(request.weight_mark_alignment * alignment_penalty * x[(q.id, m)])

    solver.Minimize(solver.Sum(objective_terms))
    status = solver.Solve()

    if status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        selected = []
        achieved_marks, total_qs, total_diff, total_diff_spread, total_bloom, total_bloom_spread = 0, 0, 0, 0, 0, 0

        for q in questions:
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

        status_str = "OPTIMAL" if status == pywraplp.Solver.OPTIMAL else "FEASIBLE"
        avg_diff = total_diff / total_qs if total_qs > 0 else 0
        spread_diff = total_diff_spread / total_qs if total_qs > 0 else 0
        avg_bloom = total_bloom / total_qs if total_qs > 0 else 0
        spread_bloom = total_bloom_spread / total_qs if total_qs > 0 else 0

        return status_str, selected, achieved_marks, total_qs, avg_diff, spread_diff, avg_bloom, spread_bloom
    else:
        return "INFEASIBLE", [], 0, 0, 0, 0, 0, 0