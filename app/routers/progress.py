from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudyProgress
from app.schemas import ProgressOut, ProgressUpdate

router = APIRouter(prefix="/progress", tags=["progress"])


def _timestamp_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=list[ProgressOut])
def list_progress(db: Session = Depends(get_db)):
    return db.query(StudyProgress).order_by(StudyProgress.subject).all()


@router.put("/{subject}", response_model=ProgressOut)
def upsert_progress(subject: str, data: ProgressUpdate, db: Session = Depends(get_db)):
    progress = db.query(StudyProgress).filter(StudyProgress.subject == subject).first()

    if progress is None:
        progress = StudyProgress(
            subject=subject,
            progress_pct=data.progress_pct,
            updated_at=_timestamp_now(),
        )
        db.add(progress)
    else:
        progress.progress_pct = data.progress_pct
        progress.updated_at = _timestamp_now()

    db.commit()
    db.refresh(progress)
    return progress
