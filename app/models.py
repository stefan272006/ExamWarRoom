from sqlalchemy import Column, Integer, String
from app.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    exam_date = Column(String, nullable=False)
    created_at = Column(String, nullable=False)


class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    duration_seconds = Column(Integer, nullable=False)
    mode = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    completed_at = Column(String, nullable=False)


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    text = Column(String, nullable=False)
    created_at = Column(String, nullable=False)


class StudyProgress(Base):
    __tablename__ = "study_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    subject = Column(String, nullable=False, unique=True)
    progress_pct = Column(Integer, nullable=False, default=0)
    updated_at = Column(String, nullable=False)
