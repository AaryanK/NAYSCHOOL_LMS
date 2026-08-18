from typing import Dict, Any
from backend.agy.base_agent import BaseAgent

class NotesGeneratorAgent(BaseAgent):
    name: str = "NotesGeneratorAgent"
    description: str = "Generates organized, readable study notes and summaries based on upload materials."

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        course_name = input_data.get("course_name", "the course")
        return {
            "status": "skeleton",
            "message": f"NotesGeneratorAgent active for '{course_name}'. Ready to digest materials.",
            "todo": [
                "Index uploaded lectures, slides, and readings",
                "Extract core definitions and concepts",
                "Compile markdown-formatted summaries and cheatsheets"
            ]
        }
