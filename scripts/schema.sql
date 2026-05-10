-- OnisLanguage PostgreSQL schema
-- Focused on: Users, Flashcards, Practice Exams, and Shared Resources

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS flashcard_decks (
    deck_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    language_focus TEXT NOT NULL DEFAULT 'Japanese',
    visibility TEXT NOT NULL DEFAULT 'public', -- public/private
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS flashcards (
    card_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deck_id UUID NOT NULL REFERENCES flashcard_decks(deck_id) ON DELETE CASCADE,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    reading TEXT,
    example_sentence TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS practice_exams (
    exam_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    topic TEXT NOT NULL,
    level TEXT NOT NULL, -- n5, n4, n3, n2, n1
    tags TEXT[] NOT NULL DEFAULT '{}',
    question_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS practice_questions (
    question_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID NOT NULL REFERENCES practice_exams(exam_id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    kind TEXT NOT NULL, -- multiple_choice, short_answer
    prompt TEXT NOT NULL,
    options JSONB NOT NULL DEFAULT '[]'::jsonb,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    UNIQUE (exam_id, position)
);

CREATE TABLE IF NOT EXISTS audio_samples (
    audio_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL, -- path on storage
    transcript_ja TEXT,
    transcript_vi TEXT,
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
