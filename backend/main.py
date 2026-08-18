import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import init_db
from backend.routers import (
    auth,
    courses,
    assignments,
    uploads,
    tutor,
    exam_prep,
    flashcards,
    lms_blackboard,
    health,
    lms,
    topics,
    practice,
    study_plan,
    learning_dashboard,
    user_profile,
    student_home,
    notifications
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (create SQLite tables automatically for local MVP)
    init_db()
    # Create the storage upload folder structure
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(base_dir, "storage", "uploads"), exist_ok=True)
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Course-aware AI learning operating system.",
    version="3.0.0",
    lifespan=lifespan,
    debug=settings.APP_DEBUG
)

# Configure CORS Origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers with the '/api' prefix
app.include_router(health.router, prefix="/api")
app.include_router(health.ai_router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(courses.router, prefix="/api")
app.include_router(assignments.course_router, prefix="/api")
app.include_router(assignments.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(tutor.router, prefix="/api")
app.include_router(exam_prep.router, prefix="/api")
app.include_router(flashcards.router, prefix="/api")
app.include_router(lms_blackboard.router, prefix="/api")
app.include_router(lms.router, prefix="/api")
app.include_router(topics.router, prefix="/api")
app.include_router(practice.router, prefix="/api")
app.include_router(study_plan.router, prefix="/api")
app.include_router(learning_dashboard.router, prefix="/api")
app.include_router(user_profile.router, prefix="/api")
app.include_router(student_home.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")

# ─── Frontend Serving ─────────────────────────────────────────────
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(root_dir, "frontend")
os.makedirs(frontend_dir, exist_ok=True)

# Serve /static/css/ and /static/js/ from frontend subdirectories
static_css_dir = os.path.join(frontend_dir, "css")
static_js_dir = os.path.join(frontend_dir, "js")
os.makedirs(static_css_dir, exist_ok=True)
os.makedirs(static_js_dir, exist_ok=True)
app.mount("/static/css", StaticFiles(directory=static_css_dir), name="static-css")
app.mount("/static/js", StaticFiles(directory=static_js_dir), name="static-js")

# Clean URL page routes — serve HTML files without .html extension
_PAGE_MAP = {
    "dashboard": "dashboard.html",
    "course": "course.html",
    "lms": "lms.html",
    "notifications": "notifications.html",
    "onboarding": "onboarding.html",
    "pricing": "pricing.html",
}

def _make_page_route(html_file: str):
    """Create a route handler that serves an HTML file."""
    file_path = os.path.join(frontend_dir, html_file)
    async def _serve_page():
        return FileResponse(file_path, media_type="text/html")
    return _serve_page

for slug, html_file in _PAGE_MAP.items():
    app.get(f"/{slug}", include_in_schema=False)(_make_page_route(html_file))

# Fallback: Serve frontend directory with html=True for / (index.html) and *.html paths
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

