from typing import Dict, Any
from backend.agy.base_agent import BaseAgent

class AssignmentUnderstandingAgent(BaseAgent):
    name: str = "AssignmentUnderstandingAgent"
    description: str = "Deconstructs assignments, homework prompts, and projects to outline requirements and suggest structures."

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        assignment_title = input_data.get("assignment_title", "")
        return {
            "status": "skeleton",
            "message": f"AssignmentUnderstandingAgent active for assignment '{assignment_title}'.",
            "analysis": {
                "key_deliverables": [],
                "suggested_approach": [],
                "implied_prerequisites": []
            },
            "todo": [
                "Parse homework PDF files or prompts",
                "Extract deliverables (e.g. format, equations to use, length requirements)",
                "Propose a structured step-by-step draft outline"
            ]
        }
