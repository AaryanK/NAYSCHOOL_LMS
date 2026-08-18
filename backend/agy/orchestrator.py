from typing import Dict, Any
from backend.ai.llm_router import LLMRouter
from backend.agy.base_agent import BaseAgent
from backend.agy.integrity_agent import IntegrityAgent
from backend.agy.homework_tutor_agent import HomeworkTutorAgent
from backend.agy.exam_prep_agent import ExamPrepAgent
from backend.agy.flashcard_agent import FlashcardAgent
from backend.agy.course_sync_agent import CourseSyncAgent
from backend.agy.syllabus_parser_agent import SyllabusParserAgent
from backend.agy.assignment_understanding_agent import AssignmentUnderstandingAgent
from backend.agy.notes_generator_agent import NotesGeneratorAgent
from backend.agy.planner_agent import PlannerAgent
from backend.agy.topic_extraction_agent import TopicExtractionAgent
from backend.agy.practice_question_agent import PracticeQuestionAgent

class Orchestrator:
    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router
        self.agents: Dict[str, BaseAgent] = {
            "integrity_check": IntegrityAgent(self.llm_router),
            "tutor": HomeworkTutorAgent(self.llm_router),
            "exam_prep": ExamPrepAgent(self.llm_router),
            "flashcards": FlashcardAgent(self.llm_router),
            "course_sync": CourseSyncAgent(),
            "syllabus_parser": SyllabusParserAgent(),
            "assignment_understanding": AssignmentUnderstandingAgent(),
            "notes_generator": NotesGeneratorAgent(),
            "planner": PlannerAgent(),
            "topic_extraction": TopicExtractionAgent(self.llm_router),
            "practice_question": PracticeQuestionAgent(self.llm_router)
        }

    async def route_and_run(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task_type.lower().strip()
        if task_type not in self.agents:
            raise ValueError(f"Orchestrator does not support task type: '{task_type}'")
        return await self.agents[task_type].run(input_data)
