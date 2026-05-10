from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class PracticeQuestion(BaseModel):
    question_id: str
    kind: Literal["multiple_choice", "short_answer", "true_false"]
    prompt: str
    options: List[str] = Field(default_factory=list)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    explanation: Optional[str] = None
    answer: Optional[str] = None


class PracticeExamCreateRequest(BaseModel):
    title: str
    topic: str = "Japanese"
    level: Literal["n5", "n4", "n3", "n2", "n1"] = "n5"
    question_count: int = Field(default=10, ge=1, le=50)
    source: Literal["backend", "client"] = "backend"
    tags: List[str] = Field(default_factory=list)
    questions: Optional[List[PracticeQuestion]] = None


class PracticeExamResponse(BaseModel):
    exam_id: str
    title: str
    topic: str
    level: str
    source: Literal["backend", "client"] = "backend"
    tags: List[str] = Field(default_factory=list)
    questions: List[PracticeQuestion]


class PracticeSubmissionRequest(BaseModel):
    answers: Dict[str, str]


class PracticeQuestionResult(BaseModel):
    question_id: str
    user_answer: Optional[str] = None
    correct_answer: str
    is_correct: bool


class PracticeSubmissionResponse(BaseModel):
    exam_id: str
    score: float
    total_questions: int
    correct_answers: int
    results: List[PracticeQuestionResult]


class PracticeExamListResponse(BaseModel):
    exams: List[PracticeExamResponse]
