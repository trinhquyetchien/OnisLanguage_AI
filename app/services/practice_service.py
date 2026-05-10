from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from app.db.models import PracticeExam, PracticeQuestion
from app.db.session import SessionLocal
from app.schemas.practice import (
    PracticeExamListResponse,
    PracticeExamResponse,
    PracticeQuestion as QuestionSchema,
    PracticeSubmissionRequest,
    PracticeSubmissionResponse,
    PracticeQuestionResult
)

class PracticeService:
    def list_exams(self) -> PracticeExamListResponse:
        db = SessionLocal()
        try:
            exams = db.query(PracticeExam).all()
            return PracticeExamListResponse(
                exams=[
                    PracticeExamResponse(
                        exam_id=str(e.exam_id),
                        title=e.title,
                        topic=e.topic,
                        level=e.level,
                        tags=e.tags,
                        question_count=e.question_count,
                        questions=[] # Fetch on demand or if needed
                    ) for e in exams
                ]
            )
        finally:
            db.close()

    def get_exam(self, exam_id: str) -> PracticeExamResponse:
        db = SessionLocal()
        try:
            exam = db.query(PracticeExam).filter(PracticeExam.exam_id == exam_id).first()
            if not exam:
                raise KeyError(f"Exam {exam_id} not found")
            
            questions = db.query(PracticeQuestion).filter(PracticeQuestion.exam_id == exam_id).order_by(PracticeQuestion.position).all()
            
            return PracticeExamResponse(
                exam_id=str(exam.exam_id),
                title=exam.title,
                topic=exam.topic,
                level=exam.level,
                tags=exam.tags,
                question_count=exam.question_count,
                questions=[
                    QuestionSchema(
                        question_id=str(q.question_id),
                        kind=q.kind,
                        prompt=q.prompt,
                        options=q.options,
                        position=q.position
                    ) for q in questions
                ]
            )
        finally:
            db.close()

    def submit_exam(self, exam_id: str, request: PracticeSubmissionRequest) -> PracticeSubmissionResponse:
        db = SessionLocal()
        try:
            questions = db.query(PracticeQuestion).filter(PracticeQuestion.exam_id == exam_id).all()
            if not questions:
                raise KeyError(f"Exam {exam_id} questions not found")

            results = []
            correct_count = 0
            
            for q in questions:
                user_ans = request.answers.get(str(q.question_id), "")
                is_correct = self._normalize_answer(user_ans) == self._normalize_answer(q.correct_answer)
                if is_correct:
                    correct_count += 1
                
                results.append(PracticeQuestionResult(
                    question_id=str(q.question_id),
                    is_correct=is_correct,
                    correct_answer=q.correct_answer,
                    user_answer=user_ans,
                    explanation=q.explanation
                ))

            return PracticeSubmissionResponse(
                exam_id=exam_id,
                score=(correct_count / len(questions)) * 100 if questions else 0,
                total_questions=len(questions),
                correct_answers=correct_count,
                results=results
            )
        finally:
            db.close()

    @staticmethod
    def _normalize_answer(answer: str | None) -> str:
        if answer is None:
            return ""
        return answer.strip().lower()

practice_service = PracticeService()
