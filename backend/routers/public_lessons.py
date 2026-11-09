"""Public electric-fields teaser: versioned curriculum and stateless answer checks.

No accounts, storage, learner profiling or LLM calls. The future DragonZpyder
lesson generator can publish reviewed content behind this same contract.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/public/lessons", tags=["public-learning-preview"])

STAGES = [
    {
        "id": "charge",
        "eyebrow": "01 / START WITH THE BASICS",
        "title": "First: what is electric charge?",
        "explanation": "Some particles carry electric charge. We call the two kinds positive and negative. Equal kinds repel one another; opposite kinds attract. Charge is a property of matter, not a little ball of electricity.",
        "example": "Think of two positively charged objects: bring them closer and they push one another away. In this simulation, the red circle is a positive charge.",
        "try_this": "Look at the arrows around the red charge. They point away from it. Drag the probe to a new position to see how the field direction changes.",
        "takeaway": "Electric field arrows show which way a tiny positive test charge would be pushed.",
        "scene": "single",
        "question_id": "field-direction",
    },
    {
        "id": "field",
        "eyebrow": "02 / WHAT IS AN ELECTRIC FIELD?",
        "title": "An invisible influence at every point",
        "explanation": "An electric field describes how a charged object affects the space around it. We can ask: if a tiny positive test charge were placed here, which way would it be pushed? The electric field is the force per unit positive test charge: E = F/q.",
        "example": "Our movable probe measures the field at its location. The probe does not create the field. Moving it tells us how the field varies across space.",
        "try_this": "Move the probe around the source charge. Watch both the arrow's direction and the field-strength number. The field is present whether we put a test charge there or not.",
        "takeaway": "Electric field belongs to the source charges and location; electric force depends on the test charge placed there.",
        "scene": "single",
        "question_id": "field-versus-force",
    },
    {
        "id": "strength",
        "eyebrow": "03 / HOW STRONG?",
        "title": "More charge, stronger field",
        "explanation": "For a single isolated point charge, the field strength is E = k|Q|/r². Q is the source charge, r is the distance to the probe, and k is a constant. Keep r fixed and double |Q|: the field doubles.",
        "example": "The slider changes the source charge in microcoulombs. Set the charge to +1 μC, then +2 μC, while leaving the probe fixed. Compare the numbers.",
        "try_this": "Change the charge slider. Remember that a negative charge reverses the direction but does not make the magnitude negative.",
        "takeaway": "At fixed distance, electric-field magnitude is proportional to the magnitude of the source charge.",
        "scene": "single",
        "question_id": "double-charge",
    },
    {
        "id": "distance",
        "eyebrow": "04 / THE INVERSE-SQUARE IDEA",
        "title": "Moving away changes everything",
        "explanation": "Electric field strength from a point charge falls with the square of distance. If you move twice as far away, the field becomes one-quarter as strong. At three times the distance, it becomes one-ninth.",
        "example": "Start with the probe roughly 1 metre away, then drag it out to roughly 2 metres. Check the field reading.",
        "try_this": "Move the probe along the horizontal axis and compare at two distances, keeping the source charge fixed.",
        "takeaway": "Distance has a squared effect on point-charge electric-field magnitude.",
        "scene": "single",
        "question_id": "double-distance",
    },
    {
        "id": "combine",
        "eyebrow": "05 / PUT TWO CHARGES TOGETHER",
        "title": "Electric fields add like arrows",
        "explanation": "When multiple charges are present, each makes a field. At a point, add those fields as vectors: their directions matter. Equal opposite charges do not always cancel. Between a positive and negative charge, both field arrows point from + toward −.",
        "example": "The scene now contains a positive and a negative charge. The probe is at the midpoint. Follow the arrows from each source separately before combining them.",
        "try_this": "Move the probe between the two charges, then outside the pair. Watch how the net field changes.",
        "takeaway": "Superposition means adding electric-field vectors, not just their magnitudes.",
        "scene": "dipole",
        "question_id": "dipole",
    },
]

_CHECKS = {
    "field-direction": {
        "prompt": "Near an isolated positive point charge, which direction does the electric field point?",
        "options": ["Away from the charge", "Toward the charge", "Always upward"],
        "correct": 0,
        "explanation": "The field points in the direction a positive test charge would be pushed. Like positive charges repel, so the arrows point away from the source.",
        "remediation": "Picture placing a tiny positive test charge next to the positive source. Would it be pushed toward or away?",
    },
    "field-versus-force": {
        "prompt": "Which statement best describes an electric field at one point in space?",
        "options": [
            "It is the force per unit positive test charge at that point",
            "It is the total charge stored at that point",
            "It is the speed at which the charge moves",
        ],
        "correct": 0,
        "explanation": "Electric field is defined by E = F/q_test for a small positive test charge. The force on an actual charge is F = qE.",
        "remediation": "The field describes the environment before you place the test charge there. Ask what quantity you get by dividing the force by the small positive test charge.",
    },
    "double-charge": {
        "prompt": "For one isolated point charge at the same distance, what happens to field magnitude if the source charge doubles?",
        "options": ["It doubles", "It quadruples", "It stays the same"],
        "correct": 0,
        "explanation": "E = k|Q|/r². At fixed r, doubling |Q| doubles E.",
        "remediation": "In E = k|Q|/r², the numerator changes while distance stays fixed.",
    },
    "double-distance": {
        "prompt": "For one isolated point charge, what happens to the field magnitude when you double the distance?",
        "options": ["It halves", "It becomes one-quarter as strong", "It stays the same"],
        "correct": 1,
        "explanation": "E scales as 1/r². Doubling distance multiplies r² by four, so field magnitude becomes one-quarter.",
        "remediation": "Pay attention to the exponent in the denominator of E = k|Q|/r².",
    },
    "dipole": {
        "prompt": "At the midpoint between equal positive and negative charges, what happens to their fields?",
        "options": ["They cancel", "They reinforce from + toward −", "Only the positive charge has a field"],
        "correct": 1,
        "explanation": "Between a + and − charge, the + field points away from + and the − field points toward −. Both point from + to −, so they reinforce.",
        "remediation": "Draw two arrows at the midpoint: one away from +, and one toward −. Which way do they point?",
    },
}


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str = Field(min_length=1, max_length=64)
    selected_index: int = Field(ge=0, le=2)


@router.get("/electric-fields")
def get_electric_fields_preview():
    """Public lesson content. Never include grading keys or private learner data."""
    return {
        "slug": "electric-fields",
        "revision": "teaser-1",
        "title": "Electric Fields, from Zero",
        "level": "true-beginner",
        "status": "public-preview",
        "origin": "NaySchool FastAPI",
        "ai_generated": False,
        "persistence": False,
        "steps": [
            {
                **stage,
                "question": {
                    "id": stage["question_id"],
                    "prompt": _CHECKS[stage["question_id"]]["prompt"],
                    "options": _CHECKS[stage["question_id"]]["options"],
                },
            }
            for stage in STAGES
        ],
    }


@router.post("/electric-fields/check")
def check_electric_fields_answer(answer: AnswerRequest):
    """Stateless evaluation: nothing is persisted or sent to a model."""
    item = _CHECKS.get(answer.question_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Unknown lesson question.")
    if answer.selected_index >= len(item["options"]):
        raise HTTPException(status_code=422, detail="Invalid answer choice.")
    correct = answer.selected_index == item["correct"]
    return {
        "question_id": answer.question_id,
        "correct": correct,
        "correct_index": item["correct"],
        "feedback": item["explanation"] if correct else item["remediation"],
        "explanation": item["explanation"],
        "persistence": False,
        "assessed_by": "deterministic-answer-key",
    }
