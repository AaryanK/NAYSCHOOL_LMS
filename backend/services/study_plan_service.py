import datetime
from sqlalchemy.orm import Session
from backend.models import StudyPlanTask, CourseTopic
from backend.services.mastery_service import get_course_mastery_dashboard

def get_study_tasks(db: Session, user_id: int, course_id: int) -> list:
    return db.query(StudyPlanTask).filter(
        StudyPlanTask.user_id == user_id,
        StudyPlanTask.course_id == course_id
    ).order_by(StudyPlanTask.due_at.asc()).all()

def create_study_task(
    db: Session,
    user_id: int,
    course_id: int,
    title: str,
    topic_id: int = None,
    description: str = None,
    due_at: datetime.datetime = None,
    priority: str = "medium",
    status: str = "pending"
) -> StudyPlanTask:
    task = StudyPlanTask(
        user_id=user_id,
        course_id=course_id,
        topic_id=topic_id,
        title=title,
        description=description,
        due_at=due_at,
        priority=priority,
        status=status,
        created_at=datetime.datetime.utcnow()
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def update_study_task(
    db: Session,
    user_id: int,
    task_id: int,
    updates: dict
) -> StudyPlanTask:
    task = db.query(StudyPlanTask).filter(
        StudyPlanTask.id == task_id,
        StudyPlanTask.user_id == user_id
    ).first()
    
    if not task:
        raise ValueError("Study plan task not found.")

    for key, val in updates.items():
        if hasattr(task, key) and val is not None:
            setattr(task, key, val)

    if updates.get("status") == "completed":
        task.completed_at = datetime.datetime.utcnow()
    elif updates.get("status") in ["pending", "in_progress"]:
        task.completed_at = None

    db.commit()
    db.refresh(task)
    return task

def generate_study_tasks_from_weaknesses(
    db: Session,
    user_id: int,
    course_id: int,
    days: int = 7
) -> list:
    # Get weakest topics sorted ascending
    weak_topics = get_course_mastery_dashboard(db, user_id, course_id)
    if not weak_topics:
        return []

    # Take the top 3 weakest topics
    target_topics = [t for t in weak_topics if t["mastery_score"] < 0.85][:3]
    if not target_topics:
        # If no weak topics, take the top 3 overall lowest mastery topics
        target_topics = weak_topics[:3]

    generated_tasks = []
    base_date = datetime.datetime.utcnow()

    # Determine priority based on mastery
    def get_priority(mastery):
        if mastery < 0.25:
            return "urgent"
        elif mastery < 0.5:
            return "high"
        elif mastery < 0.75:
            return "medium"
        else:
            return "low"

    # Tasks patterns
    task_templates = [
        ("Review topic explanation: {topic_name}", "Spend 15 minutes reviewing definition and syllabus details for {topic_name}."),
        ("Re-read related chunks for {topic_name}", "Check document uploads and read matching paragraphs for {topic_name}."),
        ("Complete 5 practice questions on {topic_name}", "Generate a practice quiz for {topic_name} and score at least 80%."),
        ("Ask tutor about confusing concept in {topic_name}", "Type a query in the chat tutor to clarify any doubts on {topic_name}.")
    ]

    # Delete previous pending study tasks to keep the board clean/regenerated
    db.query(StudyPlanTask).filter(
        StudyPlanTask.user_id == user_id,
        StudyPlanTask.course_id == course_id,
        StudyPlanTask.status == "pending"
    ).delete()
    db.commit()

    # Spread the tasks across days
    task_index = 0
    for topic in target_topics:
        topic_id = topic["topic_id"]
        topic_name = topic["topic_name"]
        mastery = topic["mastery_score"]
        priority = get_priority(mastery)

        for title_tpl, desc_tpl in task_templates:
            # Distribute due date across the day range
            due_day_offset = (task_index % days) + 1
            due_at = base_date + datetime.timedelta(days=due_day_offset)
            
            task = StudyPlanTask(
                user_id=user_id,
                course_id=course_id,
                topic_id=topic_id,
                title=title_tpl.format(topic_name=topic_name),
                description=desc_tpl.format(topic_name=topic_name),
                due_at=due_at,
                priority=priority,
                status="pending",
                created_at=base_date
            )
            db.add(task)
            generated_tasks.append(task)
            task_index += 1

    db.commit()
    for t in generated_tasks:
        db.refresh(t)

    return generated_tasks
