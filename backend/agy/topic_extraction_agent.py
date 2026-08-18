import json
import re
from typing import Dict, Any, List
from backend.agy.base_agent import BaseAgent
from backend.ai.llm_router import LLMRouter

class TopicExtractionAgent(BaseAgent):
    name: str = "TopicExtractionAgent"
    description: str = "Extracts course topics from syllabus, chunks, and metadata."

    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        chunks = input_data.get("chunks", [])
        syllabus_text = input_data.get("syllabus_text", "")
        assignments = input_data.get("assignment_titles", [])
        course_name = input_data.get("course_name", "the course")
        course_desc = input_data.get("course_description", "")
        provider = input_data.get("provider", "auto")
        model = input_data.get("model", None)

        # Prepare context for the prompt
        chunks_context = "\n".join([f"- Chunk {i+1}: {chunk[:300]}..." for i, chunk in enumerate(chunks[:20])])
        assignments_context = ", ".join(assignments) if assignments else "None"

        system_prompt = (
            "You are the TopicExtractionAgent of NaySchool.\n"
            "Your goal is to extract a structured list of main topics from the provided course materials, syllabus, assignments, and metadata.\n"
            "Guidelines:\n"
            "- Prefer topics that appear repeatedly in the materials.\n"
            "- Avoid tiny or random phrases; extract meaningful concepts.\n"
            "- Group similar concepts together.\n"
            "- Keep topic names short, clear, and distinct (e.g. 'Intro to Calculus', 'Neural Networks', not 'Page 4 concepts').\n"
            "- Return a confidence score between 0.0 and 1.0 for each topic.\n"
            "- Provide brief 'evidence' (e.g. a short quote or mention of where it appeared, like 'syllabus' or 'chunk 2').\n\n"
            "You MUST respond ONLY with a valid JSON object matching this structure:\n"
            "{\n"
            '  "topics": [\n'
            '     {"name": "Topic Name", "description": "Topic description", "confidence": 0.95, "evidence": "evidence text"}\n'
            '  ]\n'
            "}"
        )

        user_content = (
            f"Course Name: {course_name}\n"
            f"Course Description: {course_desc}\n"
            f"Assignments: {assignments_context}\n"
            f"Syllabus Preview: {syllabus_text[:2000] if syllabus_text else 'None'}\n"
            f"Course Materials Content Chunks:\n{chunks_context}\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            res = await self.llm_router.chat(messages=messages, provider=provider, model=model, temperature=0.3)
            content = res.get("content", "").strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(content)
            extracted_topics = parsed.get("topics", [])
            
            # Post-validation on extracted topics
            validated_topics = []
            for t in extracted_topics:
                if isinstance(t, dict) and t.get("name"):
                    validated_topics.append({
                        "name": str(t.get("name")),
                        "description": str(t.get("description", "")),
                        "confidence": float(t.get("confidence", 0.8)),
                        "evidence": str(t.get("evidence", ""))
                    })
            
            if not validated_topics:
                raise ValueError("No topics extracted or parsed successfully.")
                
            return {"topics": validated_topics}
        except Exception as e:
            # Fallback keyword extraction
            fallback_topics = self._fallback_extract(chunks, syllabus_text, assignments, course_name)
            return {"topics": fallback_topics}

    def _fallback_extract(self, chunks: List[str], syllabus_text: str, assignments: List[str], course_name: str) -> List[Dict[str, Any]]:
        topics = []
        
        # 1. Course title as core topic
        if course_name and course_name.lower() not in ["the course", "course"]:
            topics.append({
                "name": course_name,
                "description": f"Core overarching concepts for {course_name}",
                "confidence": 0.9,
                "evidence": "Course Name"
            })
            
        # 2. Assignments
        for title in assignments:
            if title and len(title) > 3:
                topics.append({
                    "name": title,
                    "description": f"Topic related to assignment: {title}",
                    "confidence": 0.8,
                    "evidence": "Assignment Title"
                })

        # 3. Text patterns in syllabus or chunks
        all_text = (syllabus_text or "") + "\n" + "\n".join(chunks)
        candidates = set()
        
        # Match week/chapter lines
        chapter_matches = re.findall(r'(?:Week|Chapter|Unit|Module)\s+\d+[:\-\s]+([A-Z][a-zA-Z\s,]{3,40})', all_text, re.IGNORECASE)
        for m in chapter_matches:
            candidates.add(m.strip())

        # Match markdown headers
        header_matches = re.findall(r'(?:^|\n)(?:#|##|###)\s+([A-Z][a-zA-Z\s,]{3,40})', all_text)
        for m in header_matches:
            candidates.add(m.strip())

        # Match capitalized phrases (2-4 words) that appear repeatedly
        phrase_counts = {}
        words = re.findall(r'\b[a-zA-Z]+\b', all_text)
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i+1]
            if w1[0].isupper() and w2[0].isupper() and len(w1) > 2 and len(w2) > 2:
                phrase = f"{w1} {w2}"
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        # Add high frequency phrases
        sorted_phrases = sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)
        for phrase, count in sorted_phrases[:5]:
            if count >= 2:
                candidates.add(phrase)

        # Filter candidates for stop words and duplicates
        stopwords = {"chapter", "week", "unit", "module", "lecture", "homework", "exam", "quiz", "syllabus", "assignment", "page", "grade", "course", "class"}
        for cand in candidates:
            cand_clean = re.sub(r'\s+', ' ', cand).strip()
            if not cand_clean or len(cand_clean) < 4 or len(cand_clean) > 40:
                continue
            if any(stop in cand_clean.lower() for stop in stopwords):
                continue
            # Check if name is already added
            if any(t["name"].lower() == cand_clean.lower() for t in topics):
                continue
            topics.append({
                "name": cand_clean,
                "description": f"Key concept: {cand_clean}",
                "confidence": 0.7,
                "evidence": "Extracted from text content"
            })

        # Safeguard
        if not topics:
            topics.append({
                "name": "General Syllabus Concepts",
                "description": "Primary course overview and learning outcomes.",
                "confidence": 0.6,
                "evidence": "Fallback default"
            })
            
        return topics[:10]  # Return at most 10 topics for simplicity
