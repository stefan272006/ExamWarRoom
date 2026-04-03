from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FocusSession
from app.schemas import SessionCreate, SessionOut, StatsOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _timestamp_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    session = FocusSession(
        duration_seconds=data.duration_seconds,
        mode=data.mode,
        subject=data.subject or None,
        completed_at=_timestamp_now(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/stats", response_model=StatsOut)
def get_session_stats(db: Session = Depends(get_db)):
    sessions = db.query(FocusSession).all()
    total_seconds = sum(session.duration_seconds for session in sessions)
    completed_at_values = [session.completed_at for session in sessions]

    return StatsOut(
        hours_studied=round(total_seconds / 3600, 2),
        session_count=len(sessions),
        day_streak=_calculate_day_streak(completed_at_values),
    )
