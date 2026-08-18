from sqlalchemy.orm import Session
from backend.models import Course
from backend.schemas import CourseCreate

class CourseService:
    @staticmethod
    def get_courses_by_user(db: Session, user_id: int) -> list[Course]:
        return db.query(Course).filter(Course.user_id == user_id).all()

    @staticmethod
    def get_course_by_id(db: Session, course_id: int, user_id: int) -> Course | None:
        return db.query(Course).filter(Course.id == course_id, Course.user_id == user_id).first()

    @staticmethod
    def create_course(db: Session, course_in: CourseCreate, user_id: int) -> Course:
        course = Course(
            user_id=user_id,
            name=course_in.name,
            code=course_in.code,
            instructor=course_in.instructor,
            description=course_in.description
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        return course

    @staticmethod
    def delete_course(db: Session, course_id: int, user_id: int) -> bool:
        course = db.query(Course).filter(Course.id == course_id, Course.user_id == user_id).first()
        if course:
            db.delete(course)
            db.commit()
            return True
        return False
