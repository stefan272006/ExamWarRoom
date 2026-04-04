from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FocusSession, StudyProgress
from app.router_utils import get_course_or_404, timestamp_now
from app.schemas import ProgressCreate, ProgressOut, ProgressUpdate

router = APIRouter(prefix="/progress", tags=["progress"])

CONFIDENCE_BASE = {0: 10, 1: 45, 2: 80}


def _normalize_subject(subject: str) -> str:
    subject = subject.strip()
    if not subject:
        raise HTTPException(status_code=422, detail="subject must not be blank")
    return subject


def _get_hours_by_subject(db: Session, course_id: int) -> dict[str, float]:
    rows = (
        db.query(
            FocusSession.subject,
            func.sum(FocusSession.duration_seconds).label("total_seconds"),
        )
        .filter(
            FocusSession.course_id == course_id,
            FocusSession.subject.is_not(None),
        )
        .group_by(FocusSession.subject)
        .all()
    )
    return {
        subject: (total_seconds or 0) / 3600.0
        for subject, total_seconds in rows
        if subject
    }


def _build_out(progress: StudyProgress, hours_by_subject: dict[str, float]) -> dict:
    confidence = progress.confidence if progress.confidence is not None else 0
    base = CONFIDENCE_BASE.get(confidence, CONFIDENCE_BASE[0])
    hours = hours_by_subject.get(progress.subject, 0.0)
    activity_bonus = min(20, int(hours * 4))
    return {
        "id": progress.id,
        "course_id": progress.course_id,
        "subject": progress.subject,
        "confidence": confidence,
        "progress_pct": min(100, base + activity_bonus),
        "updated_at": progress.updated_at,
    }


@router.get("", response_model=list[ProgressOut])
def list_progress(course_id: int, db: Session = Depends(get_db)):
    get_course_or_404(db, course_id)
    progress_rows = (
        db.query(StudyProgress)
        .filter(StudyProgress.course_id == course_id)
        .order_by(StudyProgress.subject)
        .all()
    )
    hours_by_subject = _get_hours_by_subject(db, course_id)
    return [_build_out(progress, hours_by_subject) for progress in progress_rows]


@router.post("", response_model=ProgressOut, status_code=201)
def create_progress(data: ProgressCreate, db: Session = Depends(get_db)):
    get_course_or_404(db, data.course_id)
    subject = _normalize_subject(data.subject)
    existing = (
        db.query(StudyProgress)
        .filter(
            StudyProgress.course_id == data.course_id,
            StudyProgress.subject == subject,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Subject already exists for this course")

    progress = StudyProgress(
        course_id=data.course_id,
        subject=subject,
        confidence=0,
        progress_pct=0,
        updated_at=timestamp_now(),
    )
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return _build_out(progress, _get_hours_by_subject(db, data.course_id))


@router.put("/{subject}", response_model=ProgressOut)
def upsert_progress(subject: str, data: ProgressUpdate, db: Session = Depends(get_db)):
    get_course_or_404(db, data.course_id)
    subject = _normalize_subject(subject)
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
            confidence=data.confidence,
            progress_pct=0,
            updated_at=timestamp_now(),
        )
        db.add(progress)
    else:
        progress.confidence = data.confidence
        progress.progress_pct = 0
        progress.updated_at = timestamp_now()

    db.commit()
    db.refresh(progress)
    return _build_out(progress, _get_hours_by_subject(db, data.course_id))


@router.delete("/{subject}", status_code=204)
def delete_progress(subject: str, course_id: int, db: Session = Depends(get_db)) -> Response:
    get_course_or_404(db, course_id)
    subject = _normalize_subject(subject)
    progress = (
        db.query(StudyProgress)
        .filter(
            StudyProgress.course_id == course_id,
            StudyProgress.subject == subject,
        )
        .first()
    )
    if progress is None:
        raise HTTPException(status_code=404, detail="Subject not found for this course")

    db.delete(progress)
    db.commit()
    return Response(status_code=204)
