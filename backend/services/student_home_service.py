import datetime
from sqlalchemy.orm import Session
from backend.models import User, UserProfile, Course, Assignment, StudyPlanTask, StudentMastery, CourseTopic, ChatSession, PracticeQuestion, StudyPlan
from backend.services.activity_service import get_study_streak

def get_assignments_due_soon(db: Session, user_id: int, days: int = 7) -> list:
    today = datetime.datetime.utcnow().date()
    max_due = today + datetime.timedelta(days=days)
    
    # Load assignments for this user
    assignments = db.query(Assignment).join(Course).filter(
        Course.user_id == user_id,
        Assignment.status != "completed"
    ).all()
    
    due_soon = []
    for a in assignments:
        if a.due_date:
            try:
                dt = datetime.datetime.strptime(a.due_date[:10], "%Y-%m-%d").date()
                if today <= dt <= max_due:
                    due_soon.append(a)
            except Exception:
                # Include as due soon if string can't be parsed but is set
                due_soon.append(a)
    return due_soon

def get_study_tasks_today(db: Session, user_id: int) -> list:
    now = datetime.datetime.utcnow()
    # End of today
    today_end = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)
    
    return db.query(StudyPlanTask).filter(
        StudyPlanTask.user_id == user_id,
        StudyPlanTask.status.in_(["pending", "in_progress"]),
        StudyPlanTask.due_at <= today_end
    ).all()

def get_weak_topics_across_courses(db: Session, user_id: int, limit: int = 5) -> list:
    masteries = db.query(StudentMastery).filter(
        StudentMastery.user_id == user_id
    ).order_by(StudentMastery.mastery_score.asc()).limit(limit).all()
    
    res = []
    for m in masteries:
        topic = db.query(CourseTopic).filter(CourseTopic.id == m.topic_id).first()
        course = db.query(Course).filter(Course.id == m.course_id).first()
        if topic and course:
            res.append({
                "topic_id": topic.id,
                "topic_name": topic.name,
                "course_id": course.id,
                "course_name": course.name,
                "mastery_score": m.mastery_score
            })
    return res

def get_recommended_actions(db: Session, user_id: int) -> list:
    courses = db.query(Course).filter(Course.user_id == user_id).all()
    actions = []
    
    for course in courses:
        # 1. No files uploaded yet
        if not course.files:
            actions.append(f"Upload your syllabus or study materials for {course.name}.")
            continue
            
        # 2. Files uploaded but not processed/embedded
        chunks_count = len(course.document_chunks)
        if chunks_count == 0:
            actions.append(f"Generate embeddings or wait for ingestion to complete for {course.name}.")
            continue
            
        # 3. Chunks exist but no topics
        topics_count = len(course.topics)
        if topics_count == 0:
            actions.append(f"Extract course topics for {course.name} to start tracking mastery.")
            continue
            
        # 4. Topics exist but no practice questions generated
        pq_exists = db.query(PracticeQuestion).filter(PracticeQuestion.course_id == course.id).first()
        if not pq_exists:
            actions.append(f"Generate practice questions for {course.name} to test your knowledge.")
            continue
            
        # 5. Weak topics exist
        weak_m = db.query(StudentMastery).filter(
            StudentMastery.course_id == course.id,
            StudentMastery.user_id == user_id,
            StudentMastery.mastery_score < 0.6
        ).first()
        if weak_m:
            topic = db.query(CourseTopic).filter(CourseTopic.id == weak_m.topic_id).first()
            if topic:
                actions.append(f"Practice weak topic '{topic.name}' in {course.name} to improve your mastery.")
                
        # 6. No exam prep plan
        ep_exists = db.query(StudyPlan).filter(StudyPlan.course_id == course.id).first()
        if not ep_exists:
            actions.append(f"Create an exam prep study plan for {course.name} to organize your test review.")

    # Generic check if no courses
    if not courses:
        actions.append("Create your first course to begin organizing your studies!")
        
    return actions[:6]

def get_student_home(db: Session, user_id: int) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    courses_count = db.query(Course).filter(Course.user_id == user_id).count()
    recent_courses = db.query(Course).filter(
        Course.user_id == user_id
    ).order_by(Course.created_at.desc()).limit(3).all()
    
    recent_chat_sessions = db.query(ChatSession).join(Course).filter(
        Course.user_id == user_id
    ).order_by(ChatSession.created_at.desc()).limit(3).all()
    
    assignments_due = get_assignments_due_soon(db, user_id)
    study_tasks = get_study_tasks_today(db, user_id)
    weak_topics = get_weak_topics_across_courses(db, user_id)
    streak = get_study_streak(db, user_id)
    recommended = get_recommended_actions(db, user_id)
    
    return {
        "user": user,
        "profile": profile,
        "courses_count": courses_count,
        "assignments_due_soon": assignments_due,
        "study_tasks_today": study_tasks,
        "weak_topics": weak_topics,
        "recent_courses": recent_courses,
        "recent_chat_sessions": recent_chat_sessions,
        "streak": streak,
        "recommended_actions": recommended
    }
