import json
from typing import Dict, Any
from backend.agy.base_agent import BaseAgent
from backend.ai.llm_router import LLMRouter

class IntegrityAgent(BaseAgent):
    name: str = "IntegrityAgent"
    description: str = "Ensures academic integrity by evaluating student requests for potential cheating."

    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        question = input_data.get("question", "")
        provider = input_data.get("provider", "auto")
        model = input_data.get("model", None)
        
        blocked_keywords = ["live exam", "proctored exam", "bypass", "cheat", "submit for me", "take this test for me", "give me the answer only"]
        caution_keywords = ["quiz", "graded", "assignment answer", "solve my homework", "solve this"]
        
        question_lower = question.lower()
        
        # Early exit for extreme keywords
        for kw in blocked_keywords:
            if kw in question_lower:
                return {
                    "classification": "blocked",
                    "reason": f"Request contains blocked academic integrity term: '{kw}'.",
                    "safe_alternative": "I cannot take exams or give direct answers. I can explain the underlying concepts if you ask for tutoring help."
                }
        
        # Build prompt for LLM double check
        system_prompt = (
            "You are the IntegrityAgent of NaySchool. Your job is to classify educational support requests. "
            "Classify the request into one of these categories: 'allowed', 'caution', 'blocked'.\n"
            "Rules:\n"
            "- 'blocked': Request is for cheating, live/proctored exams, bypass, cheating prompts, taking a test, or asking to write answers directly without explaining.\n"
            "- 'caution': Request asks for direct answers to quizzes, graded assignments, homework, but might be reformatted to tutor conceptually. "
            "For 'caution', we can continue but force tutoring/guided mode.\n"
            "- 'allowed': Request is for learning, explaining concepts, teaching, homework hints, checking completed work, generating similar problems.\n\n"
            "Format your response as a valid JSON object ONLY, with these exact fields:\n"
            "{\n"
            '  "classification": "allowed" | "caution" | "blocked",\n'
            '  "reason": "explanation of why it is classified this way",\n'
            '  "safe_alternative": "what the student can ask instead if blocked or cautioned"\n'
            "}"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User Request: {question}"}
        ]
        
        try:
            res = await self.llm_router.chat(messages=messages, provider=provider, model=model, temperature=0.0)
            content = res.get("content", "").strip()
            
            # Clean formatting if any markdown wrapper is returned
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(content)
            return {
                "classification": parsed.get("classification", "allowed"),
                "reason": parsed.get("reason", "AI check completed."),
                "safe_alternative": parsed.get("safe_alternative", None)
            }
        except Exception:
            # Fallback to local keyword rules if LLM fails
            for kw in caution_keywords:
                if kw in question_lower:
                    return {
                        "classification": "caution",
                        "reason": f"Match on caution keyword: '{kw}'",
                        "safe_alternative": "Please ask me to explain how to solve the problem step-by-step rather than asking for the final answer."
                    }
            return {
                "classification": "allowed",
                "reason": "Passed keyword integrity filter.",
                "safe_alternative": None
            }
