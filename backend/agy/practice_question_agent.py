import json
from typing import Dict, Any, List
from backend.agy.base_agent import BaseAgent
from backend.ai.llm_router import LLMRouter

class PracticeQuestionAgent(BaseAgent):
    name: str = "PracticeQuestionAgent"
    description: str = "Generates practice questions for a course topic using relevant chunks."

    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        topic = input_data.get("topic", "")
        chunks = input_data.get("chunks", [])
        difficulty = input_data.get("difficulty", "medium").lower()
        count = input_data.get("count", 5)
        provider = input_data.get("provider", "auto")
        model = input_data.get("model", None)

        # Prepare context for the prompt
        chunks_context = "\n".join([f"- Chunk {i+1}: {chunk}" for i, chunk in enumerate(chunks[:5])]) if chunks else ""

        system_prompt = (
            "You are the PracticeQuestionAgent of NaySchool.\n"
            "Your goal is to generate educational practice questions with answers and explanations.\n"
            f"Generate exactly {count} practice questions for the topic: '{topic}' at '{difficulty}' difficulty.\n\n"
            "Guidelines:\n"
            "- Focus on teaching and reinforcing understanding.\n"
            "- If relevant course material chunks are provided, base the questions on that context.\n"
            "- If no context is provided, generate general educational practice questions on the topic.\n"
            "- Avoid raw cheating or live exam dumps; focus on learning and comprehension.\n"
            "- Questions can be free response, conceptual, or calculations depending on the topic.\n\n"
            "You MUST respond ONLY with a valid JSON object matching this structure:\n"
            "{\n"
            '  "questions": [\n'
            '     {\n'
            '       "question_text": "Detailed practice question prompt?",\n'
            '       "answer_text": "Sample correct answer or expected response description",\n'
            '       "explanation": "Step-by-step educational explanation of why this answer is correct and key conceptual take-aways",\n'
            '       "difficulty": "' + difficulty + '"\n'
            '     }\n'
            '  ]\n'
            "}"
        )

        user_content = f"Topic: {topic}\nTarget Count: {count}\nDifficulty: {difficulty}\n"
        if chunks_context:
            user_content += f"Relevant Chunks from Course Material:\n{chunks_context}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            res = await self.llm_router.chat(messages=messages, provider=provider, model=model, temperature=0.6)
            content = res.get("content", "").strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(content)
            questions = parsed.get("questions", [])
            
            validated_questions = []
            for q in questions:
                if isinstance(q, dict) and q.get("question_text") and q.get("answer_text"):
                    validated_questions.append({
                        "question_text": str(q.get("question_text")),
                        "answer_text": str(q.get("answer_text")),
                        "explanation": str(q.get("explanation", "No explanation provided.")),
                        "difficulty": str(q.get("difficulty", difficulty))
                    })

            if not validated_questions:
                raise ValueError("No questions generated or parsed successfully.")

            return {"questions": validated_questions}
        except Exception as e:
            # Fallback practice question generation
            fallback_questions = self._fallback_generate(topic, difficulty, count)
            return {"questions": fallback_questions}

    def _fallback_generate(self, topic: str, difficulty: str, count: int) -> List[Dict[str, Any]]:
        questions = []
        # Templates based on difficulty
        if difficulty == "easy":
            templates = [
                ("What are the core fundamentals of {topic}?", 
                 "The basic components, concepts, and definitions that define {topic}.",
                 "Understanding the baseline definitions is the first step to mastering {topic}."),
                ("Why is {topic} important in this course?",
                 "It serves as a critical foundation for advanced topics and practical application.",
                 "Almost all subsequent chapters build upon the concepts introduced in {topic}."),
                ("Define the primary objective or goal of {topic}.",
                 "To solve key problems, represent systems, or organize information effectively.",
                 "The core goal is to provide a structured approach to related problems.")
            ]
        elif difficulty == "hard":
            templates = [
                ("Analyze a real-world scenario where {topic} might fail. What are the troubleshooting steps?", 
                 "Identify boundary conditions, resource limits, or logical assumptions that break, and apply systematic fixes.",
                 "Evaluating edge cases and failures shows a deeper mastery of {topic}."),
                ("Compare and contrast {topic} with its primary alternative methods. Under what specific conditions is {topic} inferior?",
                 "A detailed analysis of trade-offs, performance overheads, and design limitations.",
                 "Every methodology has trade-offs. Choosing when NOT to use {topic} is an advanced skill."),
                ("Explain the underlying mechanism of {topic} from first principles.",
                 "Derive or step through the mathematical, logical, or physical rules that govern {topic}.",
                 "First principles thinking helps break down complex systems into fundamental truths.")
            ]
        else: # medium
            templates = [
                ("Explain the step-by-step process of implementing or using {topic}.", 
                 "Begin with setup/assumptions, follow standard guidelines, and verify outputs.",
                 "Following a systematic implementation process ensures reliability and accuracy."),
                ("What are the main benefits and drawbacks of {topic}?",
                 "Benefits include efficiency and clarity, while drawbacks involve complexity and dependency.",
                 "Balancing pros and cons helps make informed decisions when using {topic}."),
                ("Describe how {topic} interacts with other related concepts in this field.",
                 "It fits into the larger architecture by acting as a model, tool, or framework.",
                 "Contextualizing the concept helps connect the dots in the overall syllabus.")
            ]

        for i in range(count):
            template = templates[i % len(templates)]
            questions.append({
                "question_text": template[0].format(topic=topic),
                "answer_text": template[1].format(topic=topic),
                "explanation": template[2].format(topic=topic),
                "difficulty": difficulty
            })

        return questions
