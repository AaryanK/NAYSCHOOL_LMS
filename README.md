# NaySchool 3.0: AI-Powered Learning Operating System

NaySchool 3.0 is a course-aware AI learning operating system designed to serve as a clean, production-ready local MVP. Students can manage courses, track assignments, upload study materials, consult a safety-first conceptually guided AI tutor, search indexed course chunks, generate practice questions, review 3D flashcards, and coordinate studies via AGY agents.

With Phase 6A, NaySchool becomes a **student-first learning product**: guided onboarding captures study preferences, a home dashboard surfaces what's due and what to study, chat sessions persist across visits, in-app notifications keep students on track, streaks and activity logs drive motivation, and a tiered plan system (Free / Plus / Pro) enforces fair usage limits. The responsive UI works on desktop and mobile.

> **Project status:** Active local MVP. Core student workflows are implemented and tested at the service and API layers. Production billing, real LMS sandbox validation, durable background queues, cloud OCR, and native pgvector queries remain roadmap items.

## Core Capabilities

- JWT-based student registration, login, profiles, and guided onboarding
- Course and assignment management with a unified student home dashboard
- Background ingestion for TXT, Markdown, PDF, DOCX, and PPTX materials
- Keyword, semantic, and hybrid retrieval over course content
- Course-aware tutoring with persistent chat sessions and academic-integrity guidance
- AI-generated topics, practice questions, flashcards, exam preparation, and study plans
- Mastery tracking, activity history, streaks, reminders, and usage-plan limits
- Provider routing across Ollama, OpenRouter, and DeepSeek
- Extensible Blackboard and Canvas connector architecture

## Architecture at a Glance

```text
Vanilla HTML/CSS/JavaScript frontend
                  |
             FastAPI API
                  |
       Routers -> Services -> AGY agents
                  |               |
          SQLAlchemy ORM      LLM router
                  |               |
      SQLite / PostgreSQL   Ollama / OpenRouter / DeepSeek
```

The backend keeps HTTP routing, business services, specialized AI agents, provider integrations, and persistence separate. Uploaded course materials pass through extraction, overlapping chunk generation, optional embedding, and indexed retrieval before they are supplied to AI learning workflows.

## Repository Layout

```text
backend/
  agy/          Specialized learning agents and orchestration
  ai/           LLM and embedding provider routers
  lms/          Universal LMS interfaces and provider adapters
  routers/      FastAPI endpoint definitions
  services/     Application and domain services
frontend/       Static responsive web application
tests/          Service, search, ingestion, LMS, and API tests
docs/           Architecture, security, integration, and roadmap notes
alembic/        Database migration scaffolding
```

## Why FastAPI?
- **Speed & Async Support**: Excellent performance and natively supports asynchronous operations (e.g., streaming and concurrent LLM provider querying).
- **Auto-Generated Documentation**: Exposes interactive Swagger UI docs automatically at `/docs`.
- **Typing & Validation**: Powered by Pydantic to ensure input schemas are strictly validated, preventing malformed data payloads.

## Why uv?
- **Extremely Fast**: Resolves and installs packages in seconds (built in Rust).
- **Virtual Environment Management**: Simplifies development by bundling dependencies under a local `.venv` automatically without complex toolchains.

---

## Setup Instructions

### Prerequisites
- [uv](https://github.com/astral-sh/uv) installed on your system.
- Python 3.10 or higher.

### Installation
1. Clone or open the repository.
2. Synchronize packages using `uv`:
   ```bash
   uv sync
   ```

### Configure `.env`
Create a `.env` file in the root directory (based on `.env.example`):
```env
APP_NAME="NaySchool 3.0"
APP_ENV=development
APP_DEBUG=true
DATABASE_URL=sqlite:///./nayschool.db
SECRET_KEY=your-custom-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

DEFAULT_AI_PROVIDER=auto
ALLOW_CLOUD_AI=true

# Ollama local/private configuration
OLLAMA_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.2

# OpenRouter multi-model LLM key
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_DEFAULT_MODEL=deepseek/deepseek-chat

# DeepSeek direct API key
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_DEFAULT_MODEL=deepseek-chat
```
> **Note**: Do not commit your `.env` file to git (it is ignored by default).

---

## Running the Application
To run the server:
```bash
run.bat
```
Or run directly via command line:
```bash
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Accessing the System
- **Frontend Panel**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Testing LLM Providers

### 1. Ollama (Local vs Cloud)
- **Local Ollama**: Start it and pull the required model (e.g. `llama3.2`):
  ```bash
  ollama run llama3.2
  ```
  Ensure `OLLAMA_BASE_URL` in `.env` is set to `http://localhost:11434` and `OLLAMA_API_KEY` is left blank.
- **Ollama Cloud**: Set `OLLAMA_BASE_URL=https://ollama.com` (or your private cloud URL) and provide your API credentials in `OLLAMA_API_KEY` (e.g., `OLLAMA_API_KEY=your_cloud_key`). The system will automatically attach the key as `Authorization: Bearer <key>` when making calls.

### 2. OpenRouter & DeepSeek (Cloud)
Provide valid keys in your `.env` for `OPENROUTER_API_KEY` or `DEEPSEEK_API_KEY`. When using `provider: "auto"`, the system automatically defaults to local Ollama and falls back to cloud providers if Ollama is offline and cloud AI is allowed.

---

## Uploading Materials & Background Ingestion (RAG)

### Supported File Types for Text Ingestion
- **Text & Markdown**: `.txt` and `.md` are fully extracted.
- **PDF**: `.pdf` text is extracted page-by-page using `pypdf`.
- **Word Document**: `.docx` text (paragraphs & tables) is extracted using `python-docx`.
- **PowerPoint**: `.pptx` slide shapes and speaker notes text is extracted using `python-pptx`.
- **OCR-Ready Images**: `.png`, `.jpg`, `.jpeg` files return extraction_status `unsupported` but route to an `OCRService` template placeholder for future OCR deployment.

### Background Ingestion Flow
1. **Quick Upload Response**: When a user uploads a file, it is written immediately to disk and a metadata record is created in the database with `processing_status="uploaded"`, returning instantly to the frontend.
2. **Asynchronous processing**: A FastAPI `BackgroundTask` is spawned to coordinate text extraction, chunking, and auto-embeddings generation in isolation.
3. **Robust State Monitoring**: File records track statuses: `processing_status` (`uploaded`, `extracting`, `chunking`, `embedding`, `completed`, `failed`, `partial`), `extraction_status`, `embedding_status`, `chunk_count`, and `embedded_count`.

---

## Alembic Migration Setup (Production Scaffolds)

For local development and MVP testing, NaySchool uses SQLite with auto-create tables on startup (with dynamic schema adjustments like adding columns via `ALTER TABLE`).

For production deployments, Alembic migrations are set up to handle schema changes cleanly.

### Initializing and Executing Alembic
Alembic reads `DATABASE_URL` dynamically from the environment settings.
- **Generate Migrations**:
  ```bash
  uv run alembic revision --autogenerate -m "message"
  ```
- **Apply Migrations**:
  ```bash
  uv run alembic upgrade head
  ```

---

## Docker Compose for PostgreSQL + pgvector

To run a production-ready vector and relational database:
1. Start the containers (runs PostgreSQL with `pgvector` on port `5432` and Adminer UI panel on port `8080`):
   ```bash
   docker compose up -d
   ```
2. Update your `.env` to point to the production database:
   ```env
   DATABASE_URL=postgresql+psycopg://nayschool:nayschool@localhost:5432/nayschool
   ```
3. Run migrations or let the app initialize schema dynamically.

---

## Current API Routes
- **Health Checks**:
  - `GET /api/health` — API status checker
  - `GET /api/ai/health` — Active provider check (reports Ollama local vs cloud mode)
- **Authentication**:
  - `POST /api/auth/register` — Create new accounts
  - `POST /api/auth/login` — Access token generation
  - `GET /api/auth/me` — Current user profile
- **Courses**:
  - `GET /api/courses` — List user courses
  - `POST /api/courses` — Create new manual course
  - `GET /api/courses/{course_id}` — View course details
  - `DELETE /api/courses/{course_id}` — Delete course
  - `GET /api/courses/{course_id}/chunks` — Fetch raw parsed chunks for debug
  - `POST /api/courses/{course_id}/search` — Search course text passages (supports mode: `hybrid` | `semantic` | `keyword`)
  - `POST /api/courses/{course_id}/embed` — Manually trigger embedding generation for all chunks in a course (supports `force=true`)
  - `GET /api/courses/{course_id}/embedding-status` — Get status of embedded chunks in a course
  - `GET /api/courses/{course_id}/ingestion-status` — Return complete course ingestion status summary
- **Course Files**:
  - `POST /api/courses/{course_id}/upload` — Non-blocking upload trigger (queues background ingestion)
  - `GET /api/courses/{course_id}/files` — List uploaded materials
  - `GET /api/courses/{course_id}/files/{file_id}/status` — Fetch processing status details for a file
  - `POST /api/courses/{course_id}/files/{file_id}/reprocess` — Delete file chunks and restart background ingestion
- **Assignments**:
  - `GET /api/courses/{course_id}/assignments` — Checklist
  - `POST /api/courses/{course_id}/assignments` — Add new assignment
  - `PATCH /api/assignments/{assignment_id}` — Update homework status (todo/completed)
- **AI Tutoring & Prep**:
  - `POST /api/courses/{course_id}/tutor/ask` — Conceptual homework tutor query with RAG context
  - `POST /api/courses/{course_id}/exam-prep` — Generate test study plans & questions
  - `POST /api/courses/{course_id}/flashcards/generate` — Generate study cards
  - `GET /api/courses/{course_id}/flashcards` — Fetch course flashcards
- **Student Learning Operating System (Phase 5)**:
  - `GET /api/courses/{course_id}/topics` — Get list of topics
  - `POST /api/courses/{course_id}/topics` — Create topic manually
  - `POST /api/courses/{course_id}/topics/extract` — Extract course topics automatically via AI Topic Agent
  - `POST /api/courses/{course_id}/topics/map-chunks` — Map course content chunks to extracted topics
  - `GET /api/courses/{course_id}/topics/{topic_id}` — View topic details
  - `POST /api/courses/{course_id}/practice/generate` — Generate practice quizzes for a topic
  - `GET /api/courses/{course_id}/practice` — View practice questions in a course
  - `POST /api/courses/{course_id}/practice/{question_id}/attempt` — Submit a graded practice quiz answer (AI / keyword grading)
  - `GET /api/courses/{course_id}/practice/attempts` — Get historical practice attempts
  - `GET /api/courses/{course_id}/study-tasks` — View study plan tasks
  - `POST /api/courses/{course_id}/study-tasks` — Create manual study task
  - `POST /api/courses/{course_id}/study-tasks/generate` — Auto-generate 7-day study tasks targeting weaknesses
  - `PATCH /api/study-tasks/{task_id}` — Update status or details of a study task
  - `GET /api/courses/{course_id}/learning-dashboard` — View unified course learning analytics dashboard
- **Student Productization (Phase 6A)**:
  - `GET /api/me/profile` — Get student profile & preferences
  - `PATCH /api/me/profile` — Update profile fields
  - `POST /api/me/onboarding/complete` — Submit onboarding wizard data
  - `GET /api/student/home` — Student home dashboard (due items, tasks, weak topics, streak, actions)
  - `GET /api/me/activity` — Recent study activity feed
  - `GET /api/me/streak` — Current study streak
  - `GET /api/me/plan` — Current subscription plan
  - `GET /api/me/usage` — Monthly usage counters
  - `PATCH /api/me/plan-dev` — Dev-only plan override for testing
  - `GET /api/courses/{course_id}/chat-sessions` — List saved tutor chat sessions
  - `POST /api/courses/{course_id}/chat-sessions` — Create a new chat session
  - `GET /api/courses/{course_id}/chat-sessions/{session_id}` — Get session with message history
  - `DELETE /api/courses/{course_id}/chat-sessions/{session_id}` — Delete a chat session
  - `GET /api/notifications` — List in-app notifications
  - `PATCH /api/notifications/{notification_id}/read` — Mark notification as read
  - `POST /api/courses/{course_id}/notifications/generate-study-reminders` — Generate reminders from assignments & tasks
- **LMS Connectors**:
  - `GET /api/lms/blackboard/status` — Blackboard scaffolding status
  - `POST /api/lms/blackboard/connect-placeholder` — Connection guidelines
  - `POST /api/lms/blackboard/sync-placeholder` — Mock sync response
  - `GET /api/lms/providers` — List supported LMS providers
  - `GET /api/lms/connections` — List active LMS connections
  - `POST /api/lms/{provider}/connect` — Start OAuth connection flow
  - `POST /api/lms/{connection_id}/sync` — Sync external courses/assignments
  - `GET /api/lms/{connection_id}/sync-logs` — Fetch connector logs

---

## Roadmap

- **Phase 1: Local MVP**: Manual course creation, uploads, concept tutor, exam prep, 3D flashcards.
- **Phase 1.5**: Document text parsing (.txt, .md, .pdf), simple sliding window chunking, word-boundary keyword search.
- **Phase 2 (Completed)**: Chunk embeddings generation (local/cloud), SQLite storage, cosine similarity calculations, hybrid retrieval, and context-aware tutor prompt upgrade.
- **Phase 3 (Completed)**: Background tasks, real-time file ingestion status tracking, Word (.docx) & PowerPoint (.pptx) extraction support, Alembic scaffolding, and Docker Compose PostgreSQL + pgvector setups.
- **Phase 4 (Completed)**: LMS integration architecture with Blackboard OAuth scaffolding, encrypted credentials service, and connector sync logs.
- **Phase 5 (Completed)**: Student Learning Operating System with AI topic extraction, course topic-to-chunk mapping, student mastery decay tracking, practice quiz generation & auto-grading, weakness-driven study plan scheduling, and visual learning dashboard.
- **Phase 6A (Completed)**: Student Productization — guided onboarding wizard, student home dashboard, persistent tutor chat sessions, in-app notifications & reminders, study streaks & activity logging, Free/Plus/Pro plan scaffold with usage limits, responsive mobile-friendly UI, course workspace tabs, and pricing page.
- **Phase 6B (Future)**: Instructor dashboard, LTI 1.3 tool compliance, admin metrics panel, Stripe payment integration, email/push notifications.
- **Phase 7 (Future)**: Real Blackboard/Canvas OAuth sandbox testing, pgvector native queries, Celery task queues, cloud OCR, mobile native shell.
