import os
from sqlalchemy.orm import Session
from backend.models import Course, ChatSession, ChatMessage
from backend.schemas import TutorAskRequest, TutorAskResponse, IntegrityResponse, TutorResponseDetail
from backend.agy.orchestrator import Orchestrator
from backend.services.file_service import FileService

class TutorService:
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator

    async def ask_tutor(
        self, db: Session, course_id: int, user_id: int, request: TutorAskRequest
    ) -> TutorAskResponse:
        
        # 1. Verify course ownership
        course = db.query(Course).filter(Course.id == course_id, Course.user_id == user_id).first()
        if not course:
            raise ValueError("Course not found or unauthorized access.")

        # 2. Run Integrity check
        integrity_input = {
            "question": request.question,
            "provider": request.provider,
            "model": request.model
        }
        
        integrity_res = await self.orchestrator.route_and_run("integrity_check", integrity_input)
        classification = integrity_res.get("classification", "allowed")
        reason = integrity_res.get("reason", "")
        safe_alternative = integrity_res.get("safe_alternative", None)

        integrity_response_obj = IntegrityResponse(
            classification=classification,
            reason=reason,
            safe_alternative=safe_alternative
        )

        # 3. If blocked, return early
        if classification == "blocked":
            return TutorAskResponse(
                integrity=integrity_response_obj,
                tutor_response=None
            )

        # Search course chunks using query (Hybrid RAG flow)
        from backend.services.search_service import hybrid_search_course_chunks
        from backend.schemas import CourseSearchResult
        from backend.models import DocumentChunk

        # Check if any chunks with embeddings exist
        has_embeddings = db.query(DocumentChunk).filter(
            DocumentChunk.course_id == course_id,
            DocumentChunk.embedding_json != None
        ).first() is not None

        search_mode = "hybrid" if has_embeddings else "keyword_fallback"

        try:
            chunks = await hybrid_search_course_chunks(
                db, 
                course_id, 
                request.question, 
                semantic_limit=5, 
                keyword_limit=5, 
                final_limit=5
            )
        except Exception:
            search_mode = "keyword_fallback"
            from backend.services.search_service import search_course_chunks
            raw_chunks = search_course_chunks(db, course_id, request.question, limit=5)
            max_kw = max([r["score"] for r in raw_chunks]) if raw_chunks else 0.0
            chunks = [{
                "chunk_id": r["chunk_id"],
                "course_file_id": r["course_file_id"],
                "semantic_score": 0.0,
                "keyword_score": r["score"] / max_kw if max_kw > 0 else 0.0,
                "final_score": r["score"] / max_kw if max_kw > 0 else 0.0,
                "content": r["content"]
            } for r in raw_chunks]

        retrieved_chunks = [
            CourseSearchResult(
                chunk_id=c["chunk_id"],
                course_file_id=c["course_file_id"],
                score=c.get("final_score") or c.get("score") or 0.0,
                semantic_score=c.get("semantic_score"),
                keyword_score=c.get("keyword_score"),
                final_score=c.get("final_score"),
                content=c["content"]
            ) for c in chunks
        ]
        
        context_used = len(retrieved_chunks) > 0
        
        # Format context chunks for user prompt injection
        files_context = ""
        if context_used:
            files_context += "COURSE CONTEXT:\n"
            for c in retrieved_chunks:
                files_context += f"[Chunk id={c.chunk_id}, file_id={c.course_file_id}, semantic_score={c.semantic_score}, keyword_score={c.keyword_score}, final_score={c.score}]\n{c.content}\n\n"

        # 4 & 5. Continue but force tutoring (our HomeworkTutorAgent focuses on guided learning)
        tutor_input = {
            "question": request.question,
            "provider": request.provider,
            "model": request.model,
            "temperature": request.temperature or 0.3,
            "course_name": course.name,
            "files_context": files_context,
            "context_used": context_used
        }
        
        tutor_res = await self.orchestrator.route_and_run("tutor", tutor_input)
        
        # 6. Save chat session / message
        session = None
        if request.session_id:
            session = db.query(ChatSession).filter(ChatSession.id == request.session_id, ChatSession.course_id == course_id).first()
        
        if not session:
            title = request.question[:50] + ("..." if len(request.question) > 50 else "")
            session = ChatSession(course_id=course_id, title=title)
            db.add(session)
            db.commit()
            db.refresh(session)

        # Save user query
        user_msg = ChatMessage(session_id=session.id, role="user", content=request.question)
        db.add(user_msg)

        # Build formatted assistant answer
        assistant_content = tutor_res.get("answer", "")
        if tutor_res.get("steps"):
            assistant_content += "\n\nSteps:\n" + "\n".join(f"- {s}" for s in tutor_res.get("steps"))
        if tutor_res.get("follow_up_question"):
            assistant_content += f"\n\nFollow-up Question: {tutor_res.get('follow_up_question')}"

        assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=assistant_content)
        db.add(assistant_msg)
        db.commit()

        # Log activity
        from backend.services.activity_service import log_study_activity
        log_study_activity(db, user_id=user_id, activity_type="tutor_question", course_id=course_id)

        # Build response detail
        tutor_detail = TutorResponseDetail(
            mode=tutor_res.get("mode", "guided_help"),
            provider_used=tutor_res.get("provider_used", "unknown"),
            model_used=tutor_res.get("model_used", "unknown"),
            context_used=tutor_res.get("context_used", context_used),
            answer=tutor_res.get("answer", ""),
            steps=tutor_res.get("steps", []),
            follow_up_question=tutor_res.get("follow_up_question"),
            integrity_note=tutor_res.get("integrity_note", "This is tutoring support, not direct cheating.")
        )

        return TutorAskResponse(
            integrity=integrity_response_obj,
            context_used=context_used,
            search_mode=search_mode,
            retrieved_chunks=retrieved_chunks,
            tutor_response=tutor_detail,
            session_id=session.id
        )


