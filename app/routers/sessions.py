from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FocusSession
from app.router_utils import get_course_or_404, timestamp_now
from app.schemas import SessionCreate, SessionOut, StatsOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _completed_local_date(timestamp: str):
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None:
        return parsed.date()
    return parsed.astimezone().date()


def _calculate_day_streak(completed_at_values: list[str]) -> int:
    completed_dates = {_completed_local_date(value) for value in completed_at_values}
    streak = 0
    current_day = datetime.now().astimezone().date()

    while current_day in completed_dates:
        streak += 1
        current_day -= timedelta(days=1)

    return streak


@router.post("", response_model=SessionOut, status_code=201)
def create_session(data: SessionCreate, db: Session = Depends(get_db)):
    get_course_or_404(db, data.course_id)
    session = FocusSession(
        course_id=data.course_id,
        duration_seconds=data.duration_seconds,
        mode=data.mode,
        subject=data.subject or None,
        completed_at=timestamp_now(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/stats", response_model=StatsOut)
def get_session_stats(course_id: int, db: Session = Depends(get_db)):
    course = get_course_or_404(db, course_id)
    sessions = db.query(FocusSession).filter(FocusSession.course_id == course_id).all()
    total_seconds = sum(session.duration_seconds for session in sessions)
    completed_at_values = [session.completed_at for session in sessions]

    return StatsOut(
        hours_studied=round(total_seconds / 3600.0, 2),
        session_count=len(sessions),
        day_streak=_calculate_day_streak(completed_at_values),
        course_name=course.name,
    )
