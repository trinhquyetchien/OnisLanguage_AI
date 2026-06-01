from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from app.db.models import FlashcardDeck, Flashcard
from app.db.session import SessionLocal
from app.schemas.flashcards import (
    FlashcardCreateRequest,
    FlashcardDeckCreateRequest,
    FlashcardDeckResponse,
    FlashcardResponse,
    FlashcardUpdateRequest,
)

class FlashcardService:
    def list_decks(self) -> List[FlashcardDeckResponse]:
        db = SessionLocal()
        try:
            decks = db.query(FlashcardDeck).filter(FlashcardDeck.visibility == "public").all()
            return [
                FlashcardDeckResponse(
                    deck_id=str(d.deck_id),
                    title=d.title,
                    description=d.description,
                    language_focus=d.language_focus,
                    cards=[] # Fetch on detail
                ) for d in decks
            ]
        finally:
            db.close()

    def get_deck(self, deck_id: str) -> FlashcardDeckResponse:
        db = SessionLocal()
        try:
            deck = db.query(FlashcardDeck).filter(FlashcardDeck.deck_id == deck_id).first()
            if not deck:
                raise KeyError(f"Deck {deck_id} not found")
            
            cards = db.query(Flashcard).filter(Flashcard.deck_id == deck_id).all()
            
            return FlashcardDeckResponse(
                deck_id=str(deck.deck_id),
                title=deck.title,
                description=deck.description,
                language_focus=deck.language_focus,
                cards=[
                    FlashcardResponse(
                        card_id=str(c.card_id),
                        front=c.front,
                        back=c.back,
                        reading=c.reading,
                        example_sentence=c.example_sentence
                    ) for c in cards
                ]
            )
        finally:
            db.close()

    def create_deck(self, request: FlashcardDeckCreateRequest) -> FlashcardDeckResponse:
        db = SessionLocal()
        try:
            new_deck = FlashcardDeck(
                title=request.title,
                description=request.description,
                language_focus=request.language_focus
            )
            db.add(new_deck)
            db.commit()
            db.refresh(new_deck)
            return self.get_deck(str(new_deck.deck_id))
        finally:
            db.close()

    def add_card(self, deck_id: str, request: FlashcardCreateRequest) -> FlashcardResponse:
        db = SessionLocal()
        try:
            deck = db.query(FlashcardDeck).filter(FlashcardDeck.deck_id == deck_id).first()
            if not deck:
                raise KeyError(f"Deck {deck_id} not found")

            new_card = Flashcard(
                deck_id=deck_id,
                front=request.front,
                back=request.back,
                reading=request.reading,
                example_sentence=request.example_sentence
            )
            db.add(new_card)
            db.commit()
            db.refresh(new_card)
            return FlashcardResponse(
                card_id=str(new_card.card_id),
                front=new_card.front,
                back=new_card.back,
                reading=new_card.reading,
                example_sentence=new_card.example_sentence
            )
        finally:
            db.close()

    def update_card(self, deck_id: str, card_id: str, request: FlashcardUpdateRequest) -> FlashcardResponse:
        db = SessionLocal()
        try:
            deck = db.query(FlashcardDeck).filter(FlashcardDeck.deck_id == deck_id).first()
            if not deck:
                raise KeyError(f"Deck {deck_id} not found")

            card = (
                db.query(Flashcard)
                .filter(Flashcard.card_id == card_id, Flashcard.deck_id == deck_id)
                .first()
            )
            if not card:
                raise KeyError(f"Card {card_id} not found in deck {deck_id}")

            if request.front is not None:
                card.front = request.front
            if request.back is not None:
                card.back = request.back
            if request.example_sentence is not None:
                card.example_sentence = request.example_sentence

            db.commit()
            db.refresh(card)

            return FlashcardResponse(
                card_id=str(card.card_id),
                front=card.front,
                back=card.back,
                reading=card.reading,
                example_sentence=card.example_sentence,
            )
        finally:
            db.close()

flashcard_service = FlashcardService()
