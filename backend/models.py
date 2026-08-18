import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    plan = Column(String, default="free", server_default="free")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    courses = relationship("Course", back_populates="user", cascade="all, delete-orphan")
    lms_connections = relationship("LMSConnection", back_populates="user", cascade="all, delete-orphan")

    # Phase 6A Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    study_activities = relationship("StudyActivity", back_populates="user", cascade="all, delete-orphan")
    usage_counters = relationship("UsageCounter", back_populates="user", cascade="all, delete-orphan")

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    instructor = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="courses")
    files = relationship("CourseFile", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    study_plans = relationship("StudyPlan", back_populates="course", cascade="all, delete-orphan")
    flashcards = relationship("Flashcard", back_populates="course", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="course", cascade="all, delete-orphan")
    document_chunks = relationship("DocumentChunk", back_populates="course", cascade="all, delete-orphan")

    # Phase 5 Relationships
    topics = relationship("CourseTopic", back_populates="course", cascade="all, delete-orphan")
    student_masteries = relationship("StudentMastery", back_populates="course", cascade="all, delete-orphan")
    practice_questions = relationship("PracticeQuestion", back_populates="course", cascade="all, delete-orphan")
    practice_attempts = relationship("PracticeAttempt", back_populates="course", cascade="all, delete-orphan")
    study_plan_tasks = relationship("StudyPlanTask", back_populates="course", cascade="all, delete-orphan")



class CourseFile(Base):
    __tablename__ = "course_files"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Ingestion status fields
    processing_status = Column(String, default="uploaded", nullable=False)
    extraction_status = Column(String, default="pending", nullable=True)
    embedding_status = Column(String, default="pending", nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    embedded_count = Column(Integer, default=0, nullable=False)
    processing_error = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    course = relationship("Course", back_populates="files")
    chunks = relationship("DocumentChunk", back_populates="course_file", cascade="all, delete-orphan")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(String, nullable=True)  # Store ISO format or plain string
    status = Column(String, default="todo")   # "todo", "in_progress", "completed"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # LMS fields
    external_provider = Column(String, nullable=True)
    external_id = Column(String, nullable=True)
    external_course_id = Column(String, nullable=True)

    # Relationships
    course = relationship("Course", back_populates="assignments")

class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    plan_json = Column(Text, nullable=False)  # JSON representation of the plan
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="study_plans")

class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    topic = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="flashcards")

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)     # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

class LMSConnection(Base):
    __tablename__ = "lms_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, default="blackboard")
    school_domain = Column(String, nullable=True)
    base_url = Column(String, nullable=True)
    external_user_id = Column(String, nullable=True)
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    scopes = Column(String, nullable=True)
    status = Column(String, default="disconnected", nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="lms_connections")

class LMSOAuthState(Base):
    __tablename__ = "lms_oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    state_hash = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False)
    lms_connection_id = Column(Integer, ForeignKey("lms_connections.id", ondelete="CASCADE"), nullable=False)
    code_verifier_encrypted = Column(Text, nullable=False)
    return_path = Column(String, default="/lms", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)

class LMSSyncLog(Base):
    __tablename__ = "lms_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("lms_connections.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False)
    sync_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    raw_summary_json = Column(Text, nullable=True)

class ExternalCourseMap(Base):
    __tablename__ = "external_course_maps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False)
    lms_connection_id = Column(Integer, ForeignKey("lms_connections.id", ondelete="CASCADE"), nullable=False)
    external_course_id = Column(String, nullable=False)
    internal_course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    course_file_id = Column(Integer, ForeignKey("course_files.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Embedding fields
    embedding_json = Column(Text, nullable=True)
    embedding_provider = Column(String, nullable=True)
    embedding_model = Column(String, nullable=True)
    embedding_dimension = Column(Integer, nullable=True)
    embedding_created_at = Column(DateTime, nullable=True)

    # Relationships
    course = relationship("Course", back_populates="document_chunks")
    course_file = relationship("CourseFile", back_populates="chunks")


class CourseTopic(Base):
    __tablename__ = "course_topics"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String, nullable=True)  # manual, extracted, lms, assignment, exam
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="topics")
    chunk_maps = relationship("TopicChunkMap", back_populates="topic", cascade="all, delete-orphan")
    student_masteries = relationship("StudentMastery", back_populates="topic", cascade="all, delete-orphan")
    practice_questions = relationship("PracticeQuestion", back_populates="topic")
    practice_attempts = relationship("PracticeAttempt", back_populates="topic")
    study_plan_tasks = relationship("StudyPlanTask", back_populates="topic")


class TopicChunkMap(Base):
    __tablename__ = "topic_chunk_maps"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("course_topics.id", ondelete="CASCADE"), nullable=False)
    document_chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    topic = relationship("CourseTopic", back_populates="chunk_maps")
    chunk = relationship("DocumentChunk")


class StudentMastery(Base):
    __tablename__ = "student_mastery"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("course_topics.id", ondelete="CASCADE"), nullable=False)
    mastery_score = Column(Float, default=0.0, nullable=False)
    confidence = Column(Float, default=0.0, nullable=False)
    attempts_count = Column(Integer, default=0, nullable=False)
    correct_count = Column(Integer, default=0, nullable=False)
    last_practiced_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    topic = relationship("CourseTopic", back_populates="student_masteries")
    course = relationship("Course", back_populates="student_masteries")


class PracticeQuestion(Base):
    __tablename__ = "practice_questions"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("course_topics.id", ondelete="SET NULL"), nullable=True)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    difficulty = Column(String, nullable=False)  # easy, medium, hard
    source = Column(String, nullable=True)  # generated, uploaded_material, lms
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="practice_questions")
    topic = relationship("CourseTopic", back_populates="practice_questions")
    attempts = relationship("PracticeAttempt", back_populates="practice_question", cascade="all, delete-orphan")


class PracticeAttempt(Base):
    __tablename__ = "practice_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("course_topics.id", ondelete="SET NULL"), nullable=True)
    practice_question_id = Column(Integer, ForeignKey("practice_questions.id", ondelete="SET NULL"), nullable=True)
    student_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="practice_attempts")
    topic = relationship("CourseTopic", back_populates="practice_attempts")
    practice_question = relationship("PracticeQuestion", back_populates="attempts")


class StudyPlanTask(Base):
    __tablename__ = "study_plan_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("course_topics.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, in_progress, completed, skipped
    priority = Column(String, default="medium", nullable=False)  # low, medium, high, urgent
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    course = relationship("Course", back_populates="study_plan_tasks")
    topic = relationship("CourseTopic", back_populates="study_plan_tasks")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    education_level = Column(String, nullable=True)  # middle_school, high_school, college, self_learner
    major = Column(String, nullable=True)
    school_name = Column(String, nullable=True)
    study_goal = Column(String, nullable=True)
    preferred_study_style = Column(String, nullable=True)  # step_by_step, quick_summary, practice_first, visual
    daily_study_minutes = Column(Integer, nullable=True)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="profile")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False)  # assignment, study_task, exam, system
    scheduled_for = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notifications")
    course = relationship("Course")


class StudyActivity(Base):
    __tablename__ = "study_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    activity_type = Column(String, nullable=False)  # tutor_question, practice_attempt, study_task_completed, file_uploaded, exam_prep_generated
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="study_activities")
    course = relationship("Course")


class UsageCounter(Base):
    __tablename__ = "usage_counters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    tutor_questions_count = Column(Integer, default=0, nullable=False)
    uploads_count = Column(Integer, default=0, nullable=False)
    practice_generations_count = Column(Integer, default=0, nullable=False)
    exam_prep_generations_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="usage_counters")


