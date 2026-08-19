from pydantic import BaseModel, Field
from typing import List, Optional

class Question(BaseModel):
    id: str
    bloom_level: int = Field(..., ge=1, le=6)
    difficulty_level: float = Field(..., ge=1.0, le=10.0)
    answer_length: float = Field(..., ge=1.0, le=10.0, description="1 (One word) to 10 (Multi-page essay)")

class MarkTemplate(BaseModel):
    marks: int
    count: int

class GenerationRequest(BaseModel):
    topic_id: Optional[int] = None
    blueprint_id: int = 1
    triggered_by: int = 1
    set_label: str = "SET A"
    mark_template: List[MarkTemplate]
    target_difficulty_avg: float
    target_difficulty_spread: float
    target_bloom_avg: float
    target_bloom_spread: float
    weight_diff_avg: float = 2.0
    weight_diff_spread: float = 1.5
    weight_bloom_avg: float = 2.0
    weight_bloom_spread: float = 1.5
    weight_mark_alignment: float = 3.0

class GeneratedQuestion(BaseModel):
    id: str
    assigned_marks: int
    bloom_level: int
    difficulty_level: float
    answer_length: float

class GenerationResponse(BaseModel):
    status: str
    generation_batch_id: Optional[int] = None
    set_id: Optional[int] = None
    total_marks: int
    total_questions: int
    actual_difficulty_avg: float
    actual_difficulty_spread: float
    actual_bloom_avg: float
    actual_bloom_spread: float
    selected_questions: List[GeneratedQuestion]
