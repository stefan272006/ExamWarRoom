from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudyProgress
from app.router_utils import get_course_or_404, timestamp_now
from app.schemas import ProgressOut, ProgressUpdate

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=list[ProgressOut])
def list_progress(course_id: int, db: Session = Depends(get_db)):
    get_course_or_404(db, course_id)
    return (
        db.query(StudyProgress)
        .filter(StudyProgress.course_id == course_id)
        .order_by(StudyProgress.subject)
        .all()
    )


@router.put("/{subject}", response_model=ProgressOut)
def upsert_progress(subject: str, data: ProgressUpdate, db: Session = Depends(get_db)):
    get_course_or_404(db, data.course_id)
    progress = (
        db.query(StudyProgress)
        .filter(
            StudyProgress.course_id == data.course_id,
            StudyProgress.subject == subject,
        )
        .first()
    )

    if progress is None:
        progress = StudyProgress(
            course_id=data.course_id,
            subject=subject,
            progress_pct=data.progress_pct,
            updated_at=timestamp_now(),
        )
        db.add(progress)
    else:
        progress.progress_pct = data.progress_pct
        progress.updated_at = timestamp_now()

    db.commit()
    db.refresh(progress)
    return progress
