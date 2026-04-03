from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---- Exams ----

class ExamCreate(BaseModel):
    name: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    exam_date: str = Field(min_length=1)


class ExamUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    exam_date: Optional[str] = None


class ExamOut(BaseModel):
    id: int
    name: str
    subject: str
    exam_date: str
    created_at: str

    model_config = {"from_attributes": True}


# ---- Focus Sessions ----

FocusMode = Literal["pomodoro", "short_break", "long_break", "deep_focus"]


class SessionCreate(BaseModel):
    duration_seconds: int = Field(gt=0)
    mode: FocusMode
    subject: Optional[str] = None


class SessionOut(BaseModel):
    id: int
    duration_seconds: int
    mode: str
    subject: Optional[str]
    completed_at: str

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    hours_studied: float
    session_count: int
    day_streak: int


# ---- Notes ----

class NoteCreate(BaseModel):
    text: str = Field(min_length=1)


class NoteOut(BaseModel):
    id: int
    text: str
    created_at: str

    model_config = {"from_attributes": True}


# ---- Study Progress ----

class ProgressUpdate(BaseModel):
    progress_pct: int = Field(ge=0, le=100)


class ProgressOut(BaseModel):
    id: int
    subject: str
    progress_pct: int
    updated_at: str

    model_config = {"from_attributes": True}
