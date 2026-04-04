from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Exam, StudyProgress
from app.router_utils import get_course_or_404, timestamp_now
from app.schemas import ExamCreate, ExamUpdate, ExamOut

router = APIRouter(prefix="/exams", tags=["exams"])


def _ensure_progress_subject(db: Session, course_id: int, subject: str) -> None:
    existing = (
        db.query(StudyProgress)
        .filter(
            StudyProgress.course_id == course_id,
            StudyProgress.subject == subject,
        )
        .first()
    )
    if existing is None:
        db.add(
            StudyProgress(
                course_id=course_id,
                subject=subject,
                progress_pct=0,
                confidence=0,
                updated_at=timestamp_now(),
            )
        )


@router.get("", response_model=list[ExamOut])
def list_exams(course_id: int, db: Session = Depends(get_db)):
    get_course_or_404(db, course_id)
    return (
        db.query(Exam)
        .filter(Exam.course_id == course_id)
        .order_by(Exam.exam_date)
        .all()
    )


@router.post("", response_model=ExamOut, status_code=201)
def create_exam(data: ExamCreate, db: Session = Depends(get_db)):
    get_course_or_404(db, data.course_id)
    exam = Exam(
        course_id=data.course_id,
        name=data.name,
        subject=data.subject,
        exam_date=data.exam_date,
        created_at=timestamp_now(),
    )
    db.add(exam)
    db.flush()

    _ensure_progress_subject(db, data.course_id, data.subject)

    db.commit()
    db.refresh(exam)
    return exam


@router.put("/{exam_id}", response_model=ExamOut)
def update_exam(exam_id: int, data: ExamUpdate, db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if data.name is not None:
        exam.name = data.name

    if data.subject is not None:
        exam.subject = data.subject
        _ensure_progress_subject(db, exam.course_id, data.subject)

    if data.exam_date is not None:
        exam.exam_date = data.exam_date

    db.commit()
    db.refresh(exam)
    return exam


@router.delete("/{exam_id}", status_code=204)
def delete_exam(exam_id: int, db: Session = Depends(get_db)) -> Response:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    db.delete(exam)
    db.commit()
    return Response(status_code=204)
