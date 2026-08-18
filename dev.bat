@echo off
echo Running NaySchool 3.0 development server...
uv sync
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
