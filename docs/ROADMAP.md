# NaySchool 3.0 Development Roadmap

This roadmap documents the phases required to progress NaySchool 3.0 from a local MVP to a fully compliant school learning system.

---

## Phase 1: Local MVP (Completed)
- **Course Management**: Manually add, detail, and delete courses.
- **Task Tracking**: Local checklists for homework and study targets.
- **Course Materials**: Sanitize and upload `.pdf`, `.txt`, `.md`, `.docx`, `.pptx`, `.jpg`, `.png` files.
- **Mock Blackboard Scaffold**: Initial scaffolding for Blackboard connections.

## Phase 1.5: Document Parsing & Simple RAG (Completed)
- **Ollama Cloud Integration**: Key verification and mode selection (local/cloud) in the AI router.
- **Text Extraction**: Parse text from `.txt`, `.md`, and `.pdf` files (using `pypdf`).
- **Text Chunking**: Sliding-window character parser splitting texts with boundary logic and safety checks.
- **Simple RAG Search**: Key-phrase and term-frequency scoring using word boundaries.
- **Course-Aware AI Tutoring**: Prompt injection utilizing chunk contexts to ground tutor outputs.
- **Search UI**: Frontend search forms and results listing.

## Phase 2: Semantic Embeddings & Hybrid Search (Completed)
- **Semantic Embeddings**: Convert chunks into vector embeddings using local Ollama (`nomic-embed-text`) or cloud embedding APIs.
- **SQLite Storage**: Store embedding arrays as serialized JSON strings in the local SQLite database.
- **Hybrid Retrieval Flow**: Combine semantic search (cosine similarity calculations) and keyword search, merged using score fusion: `0.70 * semantic + 0.30 * keyword`.
- **Tutor Prompt Upgrade**: Ground the AI tutor's conceptual explanations inside retrieved course context, showing detailed scores and search modes in the UI.

## Phase 3: Background Ingestion, Office Parsing & Scalable Infrastructure (Completed)
- **Background Ingestion Workers**: Transitioned file uploads to FastAPI non-blocking background workers.
- **Ingestion Tracking**: Real-time status flags (`processing_status`, `extraction_status`, `embedding_status`, `chunk_count`, `embedded_count`) and summary metrics.
- **Office Formats**: Integrated direct parsing for `.docx` and `.pptx` presentations including slide marker structure.
- **OCR Architecture Scaffold**: Scaffolded `OCRService` to allow future OCR integrations for scanned PDFs/images.
- **Alembic Scaffold**: Real database migrations support via Alembic and environment configuration.
- **Docker Compose Setup**: Spun up Postgres + pgvector and Adminer services.
- **Frontend Tracking**: Real-time status cards, polling trackers, and per-file reprocessing controls.

## Phase 4: LMS Connector Architecture & Security Scaffolding (Completed)
- **Universal LMS Package**: Implemented base abstract LMS connectors, registry, and schema conversions for multiple systems.
- **Blackboard OAuth Scaffold**: Developed authorization URL construction, code exchange endpoints, and data synchronizers.
- **Canvas Placeholder**: Created a Canvas connector mock endpoint module to confirm registry decoupling.
- **Token Cryptography**: Symmetric base64-Fernet secret encryption system with fallback to warn developers of unconfigured states.
- **Mapping & Audits**: Managed ExternalCourseMaps, sync history logs, and Assignment tracking maps.
- **Integrations Frontend**: Launched `lms.html` page rendering configurations, connect triggers, log panels, and sync option flows.

## Phase 5: Student Learning Operating System (Completed)
- **AI Topic Extraction**: Automatically discover course topics via LLM Topic Agent or title-case regex keyword matcher fallback.
- **Topic Chunk Mapping**: Create case-insensitive relevance-based maps between course topics and raw parsed document chunks.
- **Student Mastery Tracking**: Track student mastery scores on a 0.0 to 1.0 scale utilizing decay update heuristics and attempt-based confidence bounds.
- **Practice Generator & Quiz Grading**: Generate quiz questions matching topic contexts and auto-grade responses using LLMs or keyword overlap fallback.
- **Weakness-Driven Study Tasks**: Analyze weakest areas to auto-generate weekly study schedules with priority assignments.
- **Learning Dashboard**: Unified dashboard panel showing average mastery, weakness lists, upcoming study plan tasks, and practice metrics.

## Phase 6A: Student Productization (Completed)
- **Guided Onboarding**: Multi-step wizard capturing education level, major, study goal, daily study minutes, and preferred study style. Stored in `UserProfile` model with `onboarding_completed` flag.
- **Student Home Dashboard**: Central `GET /api/student/home` endpoint aggregating assignments due soon, today's study tasks, weak topics, study streak, recent courses, recent chat sessions, and contextual recommended actions.
- **Saved Tutor Chat Sessions**: Full CRUD for `ChatSession` and `ChatMessage` models. Tutor conversations persist across visits with session history sidebar in the course workspace.
- **In-App Notifications**: `Notification` model with types (`assignment`, `study_task`, `exam`, `system`). Auto-generation of study reminders from assignments and study plan tasks with deduplication. Mark-as-read support.
- **Study Streaks & Activity Logging**: `StudyActivity` model tracking tutor questions, practice attempts, uploads, task completions, and exam prep generations. Streak calculation counts consecutive days with activity.
- **Plan & Usage Scaffold**: Three-tier plan system (Free / Plus / Pro) with monthly usage limits enforced at the API level. `UsageCounter` model tracks per-action counts. Dev-only plan override endpoint for testing.
- **Pricing Page**: Frontend pricing grid showing plan tiers and feature comparisons. No payment integration yet.
- **Course Workspace Tabs**: Reorganized `course.html` into tabbed layout: Overview, Tutor, Materials, Topics, Practice, Study Plan, Exam Prep.
- **Mobile-Responsive UI**: Updated `styles.css` with responsive cards, spacing, buttons, loading states, and empty state guidance messages.
- **Frontend Pages**: `onboarding.html`, `notifications.html`, `pricing.html`, redesigned `dashboard.html`.

## Phase 6B: Instructor Layer & LTI (Future)
- Instructor control panels with enrollment tracking, checklist status, and safety violation reports.
- LTI 1.3 tool provider compliance for embedding NaySchool inside Blackboard/Canvas portals.
- Admin metrics dashboard for institutional deployments.
- Stripe payment integration for real plan billing.
- Email and push notification delivery.

## Phase 7: Production Infrastructure (Future)
- Live Blackboard/Canvas OAuth sandbox testing with real institutional credentials.
- pgvector native SQL vector search queries in PostgreSQL mode.
- Celery + Redis task queue backend for heavy processing.
- Cloud OCR integration (AWS Textract, Google Vision, or local Tesseract).
- Mobile native shell application.


