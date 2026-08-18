import json
from typing import Dict, Any
from backend.agy.base_agent import BaseAgent
from backend.ai.llm_router import LLMRouter

class ExamPrepAgent(BaseAgent):
    name: str = "ExamPrepAgent"
    description: str = "Generates customized study plans, identifies weak topics, and provides practice questions for upcoming exams."

    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        exam_title = input_data.get("exam_title", "")
        exam_date = input_data.get("exam_date", "")
        topics = input_data.get("topics", [])
        provider = input_data.get("provider", "auto")
        model = input_data.get("model", None)
        course_name = input_data.get("course_name", "the course")
        files_context = input_data.get("files_context", "")

        # Phase 5 inputs
        mastery_dashboard = input_data.get("mastery_dashboard", [])
        assignments_context = input_data.get("assignments_context", "")
        practice_attempts_context = input_data.get("practice_attempts_context", "")

        # Compute warning check
        has_extracted_topics = len(mastery_dashboard) > 0
        warning_fallback_msg = ""
        if not has_extracted_topics:
            warning_fallback_msg = "Topics have not been extracted for this course yet. We highly recommend extracting topics first to unlock personalized, mastery-driven study plans!"

        system_prompt = (
            "You are the ExamPrepAgent of NaySchool. Your goal is to help students prepare for their exams.\n"
            "Analyze the student's mastery dashboard, assignments, practice attempts, and course files to generate a personalized exam prep plan.\n\n"
            "You MUST respond ONLY with a valid JSON object matching this structure:\n"
            "{\n"
            '  "exam_title": "Upcoming Midterm",\n'
            '  "exam_date": "2026-06-15",\n'
            '  "days_until_exam": 7,\n'
            '  "priority_topics": [\n'
            '     {"topic": "Neural Networks", "mastery_score": 0.32, "reason": "Low mastery and appears often in course material"}\n'
            '  ],\n'
            '  "daily_plan": [\n'
            '     {"day": 1, "tasks": ["Review Neural Networks chapter", "Ask tutor about backprop"]}\n'
            '  ],\n'
            '  "practice_plan": ["Complete 5 questions on Neural Networks", "Review incorrect practice attempts"],\n'
            '  "review_strategy": "Detailed strategy summary...",\n'
            '  "warning": ""\n'
            "}"
            "\n\nIf the student has no topics or masteries, populate the 'warning' field with a message advising them to run 'Extract Topics' first, and fall back to general exam preparation tasks."
        )

        user_content = (
            f"Course: {course_name}\n"
            f"Exam Title: {exam_title}\n"
            f"Date: {exam_date}\n"
            f"Topics to cover: {', '.join(topics) if topics else 'General course syllabus'}\n"
            f"Course Materials Reference Context:\n{files_context}\n\n"
            f"Assignments Context:\n{assignments_context}\n\n"
            f"Practice Attempts Context:\n{practice_attempts_context}\n\n"
            f"Student Mastery Info:\n{json.dumps(mastery_dashboard)}\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            res = await self.llm_router.chat(messages=messages, provider=provider, model=model, temperature=0.4)
            content = res.get("content", "").strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(content)
            
            # Formulate response keeping both new keys and legacy keys for compatibility
            study_plan_legacy = []
            for item in parsed.get("daily_plan", []):
                study_plan_legacy.append({
                    "phase": f"Day {item.get('day', '?')}",
                    "tasks": item.get("tasks", []),
                    "focus": "Daily Focus Task"
                })

            weak_topics_legacy = [pt.get("topic", "") for pt in parsed.get("priority_topics", [])]
            practice_questions_legacy = [{"question": q, "hint": "Practice prompt", "answer_outline": "Review concepts"} for q in parsed.get("practice_plan", [])]

            return {
                # Legacy keys
                "study_plan": study_plan_legacy or parsed.get("study_plan", []),
                "weak_topics": weak_topics_legacy or parsed.get("weak_topics", []),
                "practice_questions": practice_questions_legacy or parsed.get("practice_questions", []),
                # New Phase 5 keys
                "exam_title": parsed.get("exam_title", exam_title),
                "exam_date": parsed.get("exam_date", exam_date),
                "days_until_exam": parsed.get("days_until_exam", 7),
                "priority_topics": parsed.get("priority_topics", []),
                "daily_plan": parsed.get("daily_plan", []),
                "practice_plan": parsed.get("practice_plan", []),
                "review_strategy": parsed.get("review_strategy", ""),
                "warning": parsed.get("warning", warning_fallback_msg)
            }
        except Exception as e:
            # Fallback
            return {
                # Legacy keys
                "study_plan": [
                    {"phase": "Phase 1: Conceptual Foundations", "tasks": ["Review lectures and notes.", "Summarize key definitions."], "focus": "Understanding fundamentals"},
                    {"phase": "Phase 2: Practice and Application", "tasks": ["Solve textbook problems.", "Attempt self-assessment questions."], "focus": "Applying concepts"},
                    {"phase": "Phase 3: Final Review", "tasks": ["Simulate exam conditions.", "Clarify remaining doubts."], "focus": "Test readiness"}
                ],
                "weak_topics": ["Complex application questions"],
                "practice_questions": [{"question": "Review course concepts.", "hint": "Check lecture notes.", "answer_outline": "Generic outline (fallback)"}],
                # New Phase 5 keys
                "exam_title": exam_title,
                "exam_date": exam_date,
                "days_until_exam": 7,
                "priority_topics": [
                    {"topic": "General Syllabus Concepts", "mastery_score": 0.0, "reason": "No specific topic mastery recorded yet"}
                ] if not mastery_dashboard else [
                    {"topic": pt["topic_name"], "mastery_score": pt["mastery_score"], "reason": "Target for improvement"}
                    for pt in mastery_dashboard[:3]
                ],
                "daily_plan": [
                    {"day": 1, "tasks": ["Review foundational concepts", "Read lecture summaries"]},
                    {"day": 2, "tasks": ["Solve practice problems"]},
                    {"day": 3, "tasks": ["Ask tutor questions about confusing topics"]}
                ],
                "practice_plan": ["Complete general assessment questions"],
                "review_strategy": "Iterate through course files and syllabus to build core recall. Generate practice questions using the sidebar.",
                "warning": warning_fallback_msg
            }
