from fastapi import APIRouter, HTTPException, Depends

from app.api import deps
from app.db.models import User
from app.schemas.flashcards import (
    FlashcardCreateRequest,
    FlashcardDeckCreateRequest,
    FlashcardDeckResponse,
    FlashcardResponse,
    FlashcardUpdateRequest,
)
from app.services.flashcard_service import flashcard_service

router = APIRouter()


@router.post("/decks", response_model=FlashcardDeckResponse)
async def create_deck(
    request: FlashcardDeckCreateRequest,
    current_user: User = Depends(deps.get_current_user)
):
    return flashcard_service.create_deck(request)


@router.get("/decks", response_model=list[FlashcardDeckResponse])
async def list_decks(
    current_user: User = Depends(deps.get_current_user)
):
    return flashcard_service.list_decks()


@router.get("/decks/{deck_id}", response_model=FlashcardDeckResponse)
async def get_deck(
    deck_id: str,
    current_user: User = Depends(deps.get_current_user)
):
    try:
        return flashcard_service.get_deck(deck_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/decks/{deck_id}/cards", response_model=FlashcardResponse)
async def add_card(
    deck_id: str, 
    request: FlashcardCreateRequest,
    current_user: User = Depends(deps.get_current_user)
):
    try:
        return flashcard_service.add_card(deck_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/decks/{deck_id}/cards/{card_id}", response_model=FlashcardResponse)
async def update_card(deck_id: str, card_id: str, request: FlashcardUpdateRequest):
    try:
        return flashcard_service.update_card(deck_id, card_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
