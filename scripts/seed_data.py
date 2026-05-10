import uuid
from app.db.session import SessionLocal
from app.db.models import User, FlashcardDeck, Flashcard, PracticeExam, PracticeQuestion

def seed_database():
    db = SessionLocal()
    try:
        # 1. Seed Practice Exams
        if db.query(PracticeExam).count() == 0:
            print("Seeding Practice Exams...")
            
            # JLPT N5 Exam
            n5_exam = PracticeExam(
                title="JLPT N5 - Tổng hợp kiến thức",
                topic="JLPT N5",
                level="n5",
                tags=["JLPT", "N5", "Grammar", "Vocabulary"],
                question_count=3
            )
            db.add(n5_exam)
            db.flush() # To get ID

            questions = [
                PracticeQuestion(
                    exam_id=n5_exam.exam_id,
                    position=1,
                    kind="multiple_choice",
                    prompt="「昨日」の読み方は何ですか？",
                    options=["あした", "きのう", "きょう", "おととい"],
                    correct_answer="きのう",
                    explanation="昨日 (きのう) means 'Yesterday'."
                ),
                PracticeQuestion(
                    exam_id=n5_exam.exam_id,
                    position=2,
                    kind="multiple_choice",
                    prompt="私は学生____。",
                    options=["は", "を", "です", "に"],
                    correct_answer="です",
                    explanation="Use 'です' for 'to be' in polite form."
                ),
                PracticeQuestion(
                    exam_id=n5_exam.exam_id,
                    position=3,
                    kind="multiple_choice",
                    prompt="田中さんは____へ行きますか？",
                    options=["だれ", "どこ", "いつ", "なに"],
                    correct_answer="どこ",
                    explanation="'どこ' means 'where'."
                )
            ]
            db.add_all(questions)

            # JLPT N4 Exam
            n4_exam = PracticeExam(
                title="JLPT N4 - Kanji & Từ vựng",
                topic="JLPT N4",
                level="n4",
                tags=["JLPT", "N4", "Kanji"],
                question_count=2
            )
            db.add(n4_exam)
            db.flush()

            n4_questions = [
                PracticeQuestion(
                    exam_id=n4_exam.exam_id,
                    position=1,
                    kind="multiple_choice",
                    prompt="「案内」の読み方は何ですか？",
                    options=["あんない", "あんないい", "あんせい", "おんない"],
                    correct_answer="あんない",
                    explanation="案内 (あんない) means 'Guidance/Information'."
                ),
                PracticeQuestion(
                    exam_id=n4_exam.exam_id,
                    position=2,
                    kind="multiple_choice",
                    prompt="明日、雨が____でしょう。",
                    options=["ふる", "ふって", "ふり", "ふった"],
                    correct_answer="ふる",
                    explanation="Use dictionary form with 'でしょう'."
                )
            ]
            db.add_all(n4_questions)
            
            db.commit()
            print("Successfully seeded Practice Exams.")

        # 2. Seed Flashcard Decks (Global)
        if db.query(FlashcardDeck).count() == 0:
            print("Seeding Flashcard Decks...")
            deck = FlashcardDeck(
                title="Tiếng Nhật IT căn bản",
                description="Học từ vựng lập trình, database và hệ thống.",
                language_focus="Japanese",
                tags=["IT", "Vocabulary"]
            )
            db.add(deck)
            db.flush()

            cards = [
                Flashcard(deck_id=deck.deck_id, front="開発", back="Phát triển", reading="かいはつ", example_sentence="アプリを開発する。"),
                Flashcard(deck_id=deck.deck_id, front="設計", back="Thiết kế", reading="せっけい", example_sentence="システムを設計する。"),
                Flashcard(deck_id=deck.deck_id, front="運用", back="Vận hành", reading="うんよう", example_sentence="サーバーを運用する。")
            ]
            db.add_all(cards)
            db.commit()
            print("Successfully seeded Flashcard Decks.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
