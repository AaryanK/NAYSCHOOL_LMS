from typing import Dict, Any
from backend.agy.base_agent import BaseAgent

class SyllabusParserAgent(BaseAgent):
    name: str = "SyllabusParserAgent"
    description: str = "Parses uploaded syllabus files to automatically extract course details, grading rubrics, and schedules."

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        file_path = input_data.get("file_path", "")
        return {
            "status": "skeleton",
            "message": f"SyllabusParserAgent active. Reading file '{file_path}'. Extraction ready to be implemented.",
            "extracted_data": {
                "course_name": None,
                "course_code": None,
                "instructor": None,
                "grading_scale": {},
                "schedule": []
            },
            "todo": [
                "Parse text from PDF, DOCX, or Image via OCR",
                "Use LLM with structured schemas to extract key dates and grading milestones",
                "Populate Course and Assignment tables based on parsed schedules"
            ]
        }
