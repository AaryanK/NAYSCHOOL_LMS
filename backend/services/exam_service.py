import json
from sqlalchemy.orm import Session
from backend.models import Course, StudyPlan, Assignment, PracticeAttempt
from backend.schemas import ExamPrepRequest, ExamPrepResponse, ExamPrepPlanDetail
from backend.agy.orchestrator import Orchestrator
from backend.services.file_service import FileService

class ExamService:
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator

    async def generate_exam_prep(
        self, db: Session, course_id: int, user_id: int, request: ExamPrepRequest
    ) -> ExamPrepResponse:
        
        # Verify course ownership
        course = db.query(Course).filter(Course.id == course_id, Course.user_id == user_id).first()
        if not course:
            raise ValueError("Course not found or unauthorized access.")

        # Read context from files
        files = FileService.get_course_files(db, course_id)
        files_context = ""
        if files:
            files_context = "Course uploaded files list:\n"
            for f in files:
                files_context += f"- {f.original_filename} ({f.file_type})\n"

        # Fetch assignments context
        assignments = db.query(Assignment).filter(Assignment.course_id == course_id).all()
        assignments_context = "\n".join([
            f"- Assignment: {a.title} (Due: {a.due_date or 'N/A'}, Status: {a.status or 'N/A'})" 
            for a in assignments
        ])

        # Fetch practice attempts context
        attempts = db.query(PracticeAttempt).filter(
            PracticeAttempt.user_id == user_id,
            PracticeAttempt.course_id == course_id
        ).order_by(PracticeAttempt.created_at.desc()).limit(10).all()
        practice_attempts_context = "\n".join([
            f"- Quiz Attempt on question ID {att.practice_question_id}: Score: {att.score or 0.0}, Correct: {att.is_correct}"
            for att in attempts
        ])

        # Fetch student mastery dashboard
        from backend.services.mastery_service import get_course_mastery_dashboard
        mastery_dashboard = get_course_mastery_dashboard(db, user_id, course_id)

        # Execute Exam Prep Agent
        prep_input = {
            "exam_title": request.exam_title,
            "exam_date": request.exam_date,
            "topics": request.topics,
            "provider": request.provider,
            "model": request.model,
            "course_name": course.name,
            "files_context": files_context,
            "mastery_dashboard": mastery_dashboard,
            "assignments_context": assignments_context,
            "practice_attempts_context": practice_attempts_context
        }
        
        prep_res = await self.orchestrator.route_and_run("exam_prep", prep_input)
        
        # Build schema object
        plan_detail = ExamPrepPlanDetail(
            study_plan=prep_res.get("study_plan", []),
            weak_topics=prep_res.get("weak_topics", []),
            practice_questions=prep_res.get("practice_questions", []),
            exam_title=prep_res.get("exam_title", request.exam_title),
            exam_date=prep_res.get("exam_date", request.exam_date),
            days_until_exam=prep_res.get("days_until_exam", 7),
            priority_topics=prep_res.get("priority_topics", []),
            daily_plan=prep_res.get("daily_plan", []),
            practice_plan=prep_res.get("practice_plan", []),
            review_strategy=prep_res.get("review_strategy", ""),
            warning=prep_res.get("warning", "")
        )
        
        # Save in database
        db_plan = StudyPlan(
            course_id=course_id,
            title=f"Study Plan for {request.exam_title}",
            plan_json=json.dumps(plan_detail.model_dump())
        )
        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)

        return ExamPrepResponse(
            study_plan_id=db_plan.id,
            title=db_plan.title,
            plan=plan_detail
        )
