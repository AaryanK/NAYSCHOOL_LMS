import json
from typing import Dict, Any
from backend.agy.base_agent import BaseAgent
from backend.ai.llm_router import LLMRouter

class FlashcardAgent(BaseAgent):
    name: str = "FlashcardAgent"
    description: str = "Generates educational flashcards (front/back questions/answers) for course topics."

    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        topic = input_data.get("topic", "")
        count = input_data.get("count", 10)
        provider = input_data.get("provider", "auto")
        model = input_data.get("model", None)
        course_name = input_data.get("course_name", "the course")
        files_context = input_data.get("files_context", "")

        system_prompt = (
            "You are the FlashcardAgent of NaySchool. Your goal is to help students memorize and learn key terms and concepts.\n"
            f"Generate exactly {count} flashcards for the given topic.\n"
            "Flashcards should have a clear, concise question/term on the 'front', and the detailed explanation/answer on the 'back'.\n\n"
            "You MUST respond ONLY with a valid JSON object matching this structure:\n"
            "{\n"
            '  "flashcards": [\n'
            '     {"front": "term or question", "back": "definition or answer explanation", "topic": "subtopic or category"}\n'
            '  ]\n'
            "}"
        )

        user_content = f"Course: {course_name}\nTopic of interest: {topic}\nTarget Count: {count}\n"
        if files_context:
            user_content += f"Course Materials Reference Context:\n{files_context}\n\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            res = await self.llm_router.chat(messages=messages, provider=provider, model=model, temperature=0.5)
            content = res.get("content", "").strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(content)
            return {
                "flashcards": parsed.get("flashcards", [])
            }
        except Exception:
            return {
                "flashcards": [
                    {
                        "front": f"What is a core concept under {topic}?",
                        "back": f"A primary element that forms the foundation of understanding {topic}. Review textbook notes for full context.",
                        "topic": topic
                    }
                ]
            }
