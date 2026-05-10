from sqlalchemy import Column, String, DateTime, Text, ARRAY, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.db.session import Base

class User(Base):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FlashcardDeck(Base):
    __tablename__ = "flashcard_decks"
    deck_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(UUID(as_uuid=True), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    language_focus = Column(String, default="Japanese")
    visibility = Column(String, default="public")
    tags = Column(ARRAY(Text), default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Flashcard(Base):
    __tablename__ = "flashcards"
    card_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deck_id = Column(UUID(as_uuid=True), nullable=False)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    reading = Column(Text, nullable=True)
    example_sentence = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PracticeExam(Base):
    __tablename__ = "practice_exams"
    exam_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(UUID(as_uuid=True), nullable=True)
    title = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    level = Column(String, nullable=False) # n5, n4, n3, n2, n1
    tags = Column(ARRAY(Text), default=[])
    question_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PracticeQuestion(Base):
    __tablename__ = "practice_questions"
    question_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id = Column(UUID(as_uuid=True), nullable=False)
    position = Column(Integer, nullable=False)
    kind = Column(String, nullable=False) # multiple_choice, short_answer
    prompt = Column(Text, nullable=False)
    options = Column(JSONB, default=[])
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)

