from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Course, Exam, Flashcard, FocusSession, Question, StudyProgress, UploadedFile, Video
from app.router_utils import timestamp_now
from app.schemas import CourseCreate, CourseOut

router = APIRouter(prefix="/courses", tags=["courses"])

UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / "static" / "uploads"


def _backfill_legacy_course_data(db: Session, course_id: int) -> None:
    for model in (Exam, FocusSession, StudyProgress, UploadedFile, Video, Question, Flashcard):
        db.query(model).filter(model.course_id.is_(None)).update(
            {model.course_id: course_id},
            synchronize_session=False,
        )


@router.get("", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db)):
    return db.query(Course).order_by(Course.created_at, Course.id).all()


@router.post("", response_model=CourseOut, status_code=201)
def create_course(data: CourseCreate, db: Session = Depends(get_db)):
    existing = db.query(Course).filter(Course.user_id == 1, Course.name == data.name).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Course already exists")

    had_no_courses = db.query(Course.id).first() is None
    course = Course(name=data.name, created_at=timestamp_now())
    db.add(course)
    db.flush()

    if had_no_courses:
        _backfill_legacy_course_data(db, course.id)

    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: int, db: Session = Depends(get_db)) -> Response:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    uploaded_files = db.query(UploadedFile).filter(UploadedFile.course_id == course_id).all()
    for uploaded_file in uploaded_files:
        (UPLOAD_ROOT / uploaded_file.section / uploaded_file.stored_name).unlink(missing_ok=True)
        db.delete(uploaded_file)

    for model in (Exam, FocusSession, StudyProgress, Video, Question, Flashcard):
        db.query(model).filter(model.course_id == course_id).delete(synchronize_session=False)

    db.delete(course)
    db.commit()
    return Response(status_code=204)
