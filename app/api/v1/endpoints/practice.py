from fastapi import APIRouter, HTTPException, Depends

from app.api import deps
from app.db.models import User
from app.schemas.practice import (
    PracticeExamCreateRequest,
    PracticeExamListResponse,
    PracticeExamResponse,
    PracticeSubmissionRequest,
    PracticeSubmissionResponse,
)
from app.services.practice_service import practice_service

router = APIRouter()


@router.get("/exams", response_model=PracticeExamListResponse)
async def list_exams(
    current_user: User = Depends(deps.get_current_user)
):
    return practice_service.list_exams()


@router.get("/exams/{exam_id}", response_model=PracticeExamResponse)
async def get_exam(
    exam_id: str,
    current_user: User = Depends(deps.get_current_user)
):
    try:
        return practice_service.get_exam(exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/exams/{exam_id}/submit", response_model=PracticeSubmissionResponse)
async def submit_exam(
    exam_id: str, 
    request: PracticeSubmissionRequest,
    current_user: User = Depends(deps.get_current_user)
):
    try:
        return practice_service.submit_exam(exam_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
