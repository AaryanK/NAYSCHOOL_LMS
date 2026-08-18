import json
from typing import Dict, Any
from backend.agy.base_agent import BaseAgent
from backend.ai.llm_router import LLMRouter

class HomeworkTutorAgent(BaseAgent):
    name: str = "HomeworkTutorAgent"
    description: str = "Guides students through homework conceptually instead of giving copy-paste answers."

    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        question = input_data.get("question", "")
        provider = input_data.get("provider", "auto")
        model = input_data.get("model", None)
        temperature = input_data.get("temperature", 0.3)
        course_name = input_data.get("course_name", "the course")
        files_context = input_data.get("files_context", "")
        context_used = input_data.get("context_used", False)

        system_prompt = (
            "You are NaySchool Tutor, a course-aware AI tutor. You teach from the student's uploaded course materials when relevant. "
            "Use the provided retrieved context as the primary source. If the context does not fully answer the question, say so clearly and then explain generally. "
            "Do not assist with cheating, live exams, proctored exams, bypassing restrictions, or submitting dishonest work. "
            "Prefer conceptual explanation, guided steps, hints, similar examples, and checking the student's reasoning.\n\n"
            "Style Guide:\n"
            "- Explain concepts in simple terms.\n"
            "- Break down the problem solving process into steps.\n"
            "- Provide hints or similar illustrative examples.\n"
            "- Never provide direct copy-paste solutions for graded assignments.\n"
            "- Ask a friendly follow-up question to test the student's understanding.\n\n"
            "You MUST respond ONLY with a valid JSON object matching this structure:\n"
            "{\n"
            '  "answer": "A concept explanation or hint guiding them. If context was not used or not found, clearly state that no relevant uploaded course context was found, and answer generally.",\n'
            '  "steps": ["Step 2 explanation", "Step 3 explanation", ...],\n'
            '  "follow_up_question": "A conceptual follow-up question to verify their understanding"\n'
            "}"
        )

        user_content = f"Course: {course_name}\n"
        if files_context:
            user_content += f"{files_context}\n"
        else:
            user_content += "No relevant uploaded course context was found.\n\n"
        user_content += f"STUDENT QUESTION:\n{question}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            res = await self.llm_router.chat(messages=messages, provider=provider, model=model, temperature=temperature)
            content = res.get("content", "").strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(content)
            
            return {
                "mode": "guided_help",
                "provider_used": res.get("provider", provider),
                "model_used": res.get("model", "unknown"),
                "context_used": context_used,
                "answer": parsed.get("answer", content),
                "steps": parsed.get("steps", []),
                "follow_up_question": parsed.get("follow_up_question", "Does this explanation make sense? What part would you like to explore next?"),
                "integrity_note": "This is tutoring support, not direct cheating."
            }
        except Exception as e:
            return {
                "mode": "guided_help",
                "provider_used": "fallback",
                "model_used": "none",
                "context_used": context_used,
                "answer": f"I had trouble parsing the AI response, but here is some guidance: Please break down the question and look at the underlying equations or definitions. (Error: {str(e)})",
                "steps": ["Review the core textbook definitions.", "List the variables and values you know.", "Draft a solution step-by-step."],
                "follow_up_question": "What is the specific step you are stuck on?",
                "integrity_note": "Tutoring agent fallback mode."
            }
