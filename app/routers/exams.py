from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Exam, StudyProgress
from app.schemas import ExamCreate, ExamUpdate, ExamOut

router = APIRouter(prefix="/exams", tags=["exams"])


@router.get("", response_model=list[ExamOut])
def list_exams(db: Session = Depends(get_db)):
    return db.query(Exam).order_by(Exam.exam_date).all()


@router.post("", response_model=ExamOut, status_code=201)
def create_exam(data: ExamCreate, db: Session = Depends(get_db)):
    exam = Exam(
        name=data.name,
        subject=data.subject,
        exam_date=data.exam_date,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(exam)
    db.flush()

    # Auto-create study progress entry for new subjects
    existing = db.query(StudyProgress).filter(StudyProgress.subject == data.subject).first()
    if not existing:
        progress = StudyProgress(
            subject=data.subject,
            progress_pct=0,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(progress)

    db.commit()
    db.refresh(exam)
    return exam


@router.put("/{exam_id}", response_model=ExamOut)
def update_exam(exam_id: int, data: ExamUpdate, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if data.name is not None:
        exam.name = data.name
    if data.subject is not None:
        exam.subject = data.subject
    if data.exam_date is not None:
        exam.exam_date = data.exam_date
    db.commit()
    db.refresh(exam)
    return exam


@router.delete("/{exam_id}", status_code=204)
def delete_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    db.delete(exam)
    db.commit()
