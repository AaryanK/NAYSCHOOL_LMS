from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime

# Token/Auth
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# User
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    plan: Optional[str] = "free"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Course
class CourseBase(BaseModel):
    name: str
    code: Optional[str] = None
    instructor: Optional[str] = None
    description: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseResponse(CourseBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# CourseFile
class CourseFileResponse(BaseModel):
    id: int
    course_id: int
    filename: str
    original_filename: str
    file_path: str
    file_type: Optional[str] = None
    uploaded_at: datetime
    processing_status: str
    extraction_status: Optional[str] = None
    embedding_status: Optional[str] = None
    chunk_count: int
    embedded_count: int
    processing_error: Optional[str] = None
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Assignment
class AssignmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = "todo"  # "todo", "in_progress", "completed"

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None

class AssignmentResponse(AssignmentBase):
    id: int
    course_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# StudyPlan
class StudyPlanBase(BaseModel):
    title: str
    plan_json: str

class StudyPlanResponse(StudyPlanBase):
    id: int
    course_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Flashcard
class FlashcardBase(BaseModel):
    front: str
    back: str
    topic: Optional[str] = None

class FlashcardCreate(FlashcardBase):
    pass

class FlashcardResponse(FlashcardBase):
    id: int
    course_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Tutor
class TutorAskRequest(BaseModel):
    question: str
    provider: Optional[str] = "auto"
    model: Optional[str] = None
    temperature: Optional[float] = 0.3
    session_id: Optional[int] = None

class IntegrityResponse(BaseModel):
    classification: str  # allowed, caution, blocked
    reason: str
    safe_alternative: Optional[str] = None

class CourseSearchResult(BaseModel):
    chunk_id: int
    course_file_id: int
    score: float
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None
    final_score: Optional[float] = None
    content: str

    model_config = ConfigDict(from_attributes=True)

class TutorResponseDetail(BaseModel):
    mode: str
    provider_used: str
    model_used: str
    context_used: bool = False
    answer: str
    steps: List[str] = []
    follow_up_question: Optional[str] = None
    integrity_note: Optional[str] = None

class TutorAskResponse(BaseModel):
    integrity: IntegrityResponse
    context_used: bool = False
    search_mode: Optional[str] = None
    retrieved_chunks: List[CourseSearchResult] = []
    tutor_response: Optional[TutorResponseDetail] = None
    session_id: Optional[int] = None


# Exam Prep
class ExamPrepRequest(BaseModel):
    exam_title: str
    exam_date: Optional[str] = None
    topics: List[str] = []
    provider: Optional[str] = "auto"
    model: Optional[str] = None

class ExamPrepPlanDetail(BaseModel):
    # Legacy fields
    study_plan: Optional[List[Dict[str, Any]]] = None
    weak_topics: Optional[List[str]] = None
    practice_questions: Optional[List[Dict[str, Any]]] = None

    # Phase 5 fields
    exam_title: Optional[str] = None
    exam_date: Optional[str] = None
    days_until_exam: Optional[int] = None
    priority_topics: Optional[List[Dict[str, Any]]] = None
    daily_plan: Optional[List[Dict[str, Any]]] = None
    practice_plan: Optional[List[Any]] = None
    review_strategy: Optional[str] = None
    warning: Optional[str] = None

class ExamPrepResponse(BaseModel):
    study_plan_id: int
    title: str
    plan: ExamPrepPlanDetail

# Flashcard Generation
class FlashcardGenerateRequest(BaseModel):
    topic: str
    count: Optional[int] = 10
    provider: Optional[str] = "auto"
    model: Optional[str] = None

class FlashcardGenerateResponse(BaseModel):
    flashcards: List[FlashcardBase]

class DocumentChunkResponse(BaseModel):
    id: int
    course_file_id: int
    course_id: int
    chunk_index: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CourseSearchRequest(BaseModel):
    query: str
    mode: Optional[str] = "hybrid"
    limit: Optional[int] = 5

class CourseSearchResponse(BaseModel):
    mode: str
    results: List[CourseSearchResult]

class CourseFileUploadResponse(BaseModel):
    file: CourseFileResponse
    message: str
    processing_status: str
    status_url: str

    model_config = ConfigDict(from_attributes=True)

class CourseFileStatusResponse(BaseModel):
    file_id: int
    course_id: int
    filename: str
    processing_status: str
    extraction_status: Optional[str] = None
    embedding_status: Optional[str] = None
    chunk_count: int
    embedded_count: int
    processing_error: Optional[str] = None
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CourseIngestionStatusSummary(BaseModel):
    course_id: int
    files_total: int
    completed: int
    processing: int
    failed: int
    chunks_total: int
    embedded_total: int
    files: List[CourseFileStatusResponse]

    model_config = ConfigDict(from_attributes=True)


# Phase 5 Schemas

class CourseTopicCreate(BaseModel):
    name: str
    description: Optional[str] = None
    source: Optional[str] = "manual"  # manual, extracted, lms, assignment, exam
    confidence: Optional[float] = None

class CourseTopicResponse(BaseModel):
    id: int
    course_id: int
    name: str
    description: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentMasteryResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    topic_id: int
    mastery_score: float
    confidence: float
    attempts_count: int
    correct_count: int
    last_practiced_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PracticeQuestionCreate(BaseModel):
    question_text: str
    answer_text: str
    explanation: Optional[str] = None
    difficulty: str  # easy, medium, hard
    source: Optional[str] = "generated"  # generated, uploaded_material, lms

class PracticeQuestionGenerateRequest(BaseModel):
    topic_id: Optional[int] = None
    count: Optional[int] = 5
    difficulty: Optional[str] = "medium"
    provider: Optional[str] = "auto"
    model: Optional[str] = None

class PracticeQuestionResponse(BaseModel):
    id: int
    course_id: int
    topic_id: Optional[int] = None
    question_text: str
    answer_text: str
    explanation: Optional[str] = None
    difficulty: str
    source: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PracticeAttemptCreate(BaseModel):
    student_answer: str
    topic_id: Optional[int] = None
    practice_question_id: Optional[int] = None

class PracticeAttemptGradeRequest(BaseModel):
    student_answer: str
    provider: Optional[str] = "auto"
    model: Optional[str] = None

class PracticeAttemptResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    topic_id: Optional[int] = None
    practice_question_id: Optional[int] = None
    student_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudyPlanTaskCreate(BaseModel):
    topic_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    status: Optional[str] = "pending"
    priority: Optional[str] = "medium"

class StudyPlanTaskResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    topic_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    status: str
    priority: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class StudyPlanTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    status: Optional[str] = None
    priority: Optional[str] = None


class TopicExtractionRequest(BaseModel):
    provider: Optional[str] = "auto"
    model: Optional[str] = None

class ExtractedTopic(BaseModel):
    name: str
    description: str
    confidence: float
    evidence: Optional[str] = None

class TopicExtractionResponse(BaseModel):
    topics: List[ExtractedTopic]


class CourseLearningDashboardResponse(BaseModel):
    course: CourseResponse
    topics_count: int
    chunks_count: int
    practice_questions_count: int
    attempts_count: int
    average_mastery: float
    weak_topics: List[Any]
    strong_topics: List[Any]
    upcoming_study_tasks: List[StudyPlanTaskResponse]
    recent_attempts: List[Any]


# Phase 6A Student Productization Schemas

class UserProfileCreate(BaseModel):
    education_level: Optional[str] = None
    major: Optional[str] = None
    school_name: Optional[str] = None
    study_goal: Optional[str] = None
    preferred_study_style: Optional[str] = None
    daily_study_minutes: Optional[int] = None

class UserProfileUpdate(BaseModel):
    education_level: Optional[str] = None
    major: Optional[str] = None
    school_name: Optional[str] = None
    study_goal: Optional[str] = None
    preferred_study_style: Optional[str] = None
    daily_study_minutes: Optional[int] = None

class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    education_level: Optional[str] = None
    major: Optional[str] = None
    school_name: Optional[str] = None
    study_goal: Optional[str] = None
    preferred_study_style: Optional[str] = None
    daily_study_minutes: Optional[int] = None
    onboarding_completed: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class OnboardingCompleteRequest(BaseModel):
    education_level: str
    major: Optional[str] = None
    school_name: Optional[str] = None
    study_goal: str
    preferred_study_style: str
    daily_study_minutes: int

class ChatSessionCreate(BaseModel):
    title: Optional[str] = None

class ChatSessionResponse(BaseModel):
    id: int
    course_id: int
    title: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StudentHomeResponse(BaseModel):
    user: UserResponse
    profile: Optional[UserProfileResponse] = None
    courses_count: int
    assignments_due_soon: List[AssignmentResponse]
    study_tasks_today: List[StudyPlanTaskResponse]
    weak_topics: List[Any]
    recent_courses: List[CourseResponse]
    recent_chat_sessions: List[ChatSessionResponse]
    streak: Dict[str, Any]
    recommended_actions: List[str]

    model_config = ConfigDict(from_attributes=True)

class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatSessionDetailResponse(BaseModel):
    id: int
    course_id: int
    title: str
    created_at: datetime
    messages: List[ChatMessageResponse]

    model_config = ConfigDict(from_attributes=True)

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    course_id: Optional[int] = None
    title: str
    message: str
    notification_type: str
    scheduled_for: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StudyActivityResponse(BaseModel):
    id: int
    user_id: int
    course_id: Optional[int] = None
    activity_type: str
    metadata_json: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StreakResponse(BaseModel):
    current_streak_days: int
    active_today: bool
    last_activity_at: Optional[datetime] = None

class UsageCounterResponse(BaseModel):
    id: int
    user_id: int
    period_start: datetime
    period_end: datetime
    tutor_questions_count: int
    uploads_count: int
    practice_generations_count: int
    exam_prep_generations_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PlanUpdateDevRequest(BaseModel):
    plan: str



