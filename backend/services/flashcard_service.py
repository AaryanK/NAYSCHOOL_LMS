from sqlalchemy.orm import Session
from backend.models import Course, Flashcard
from backend.schemas import FlashcardGenerateRequest, FlashcardGenerateResponse, FlashcardBase
from backend.agy.orchestrator import Orchestrator
from backend.services.file_service import FileService

class FlashcardService:
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator

    async def generate_flashcards(
        self, db: Session, course_id: int, user_id: int, request: FlashcardGenerateRequest
    ) -> FlashcardGenerateResponse:
        
        # Verify course ownership
        course = db.query(Course).filter(Course.id == course_id, Course.user_id == user_id).first()
        if not course:
            raise ValueError("Course not found or unauthorized access.")

        # Read context
        files = FileService.get_course_files(db, course_id)
        files_context = ""
        if files:
            files_context = "Course uploaded files list:\n"
            for f in files:
                files_context += f"- {f.original_filename} ({f.file_type})\n"

        # Execute Flashcard Agent
        card_input = {
            "topic": request.topic,
            "count": request.count or 10,
            "provider": request.provider,
            "model": request.model,
            "course_name": course.name,
            "files_context": files_context
        }
        
        card_res = await self.orchestrator.route_and_run("flashcards", card_input)
        
        cards_list = []
        for c in card_res.get("flashcards", []):
            front = c.get("front", "")
            back = c.get("back", "")
            topic = c.get("topic", request.topic)
            
            if front and back:
                # Save to database
                db_card = Flashcard(
                    course_id=course_id,
                    front=front,
                    back=back,
                    topic=topic
                )
                db.add(db_card)
                cards_list.append(FlashcardBase(front=front, back=back, topic=topic))
        
        db.commit()
        return FlashcardGenerateResponse(flashcards=cards_list)

    @staticmethod
    def get_course_flashcards(db: Session, course_id: int) -> list[Flashcard]:
        return db.query(Flashcard).filter(Flashcard.course_id == course_id).all()
