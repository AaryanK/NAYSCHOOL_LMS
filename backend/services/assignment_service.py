from sqlalchemy.orm import Session
from backend.models import Assignment
from backend.schemas import AssignmentCreate, AssignmentUpdate

class AssignmentService:
    @staticmethod
    def get_assignments_by_course(db: Session, course_id: int) -> list[Assignment]:
        return db.query(Assignment).filter(Assignment.course_id == course_id).all()

    @staticmethod
    def get_assignment_by_id(db: Session, assignment_id: int) -> Assignment | None:
        return db.query(Assignment).filter(Assignment.id == assignment_id).first()

    @staticmethod
    def create_assignment(db: Session, course_id: int, assignment_in: AssignmentCreate) -> Assignment:
        assignment = Assignment(
            course_id=course_id,
            title=assignment_in.title,
            description=assignment_in.description,
            due_date=assignment_in.due_date,
            status=assignment_in.status or "todo"
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def update_assignment(db: Session, assignment_id: int, assignment_in: AssignmentUpdate) -> Assignment | None:
        db_assign = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not db_assign:
            return None
        
        update_data = assignment_in.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(db_assign, key, val)

        db.commit()
        db.refresh(db_assign)
        return db_assign
