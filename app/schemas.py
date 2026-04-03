from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def _strip_required_text(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be blank")
    return value


def _strip_optional_text(value: Optional[str], field_name: str) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be blank")
    return value


# ---- Courses ----

class CourseCreate(BaseModel):
    name: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return _strip_required_text(value, "name")


class CourseOut(BaseModel):
    id: int
    name: str
    created_at: str

    model_config = {"from_attributes": True}


# ---- Exams ----

class ExamCreate(BaseModel):
    name: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    exam_date: str = Field(min_length=1)
    course_id: int = Field(gt=0)

    @field_validator("name", "subject", "exam_date")
    @classmethod
    def strip_required_fields(cls, value: str, info) -> str:
        return _strip_required_text(value, info.field_name)


class ExamUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    exam_date: Optional[str] = None

    @field_validator("name", "subject", "exam_date")
    @classmethod
    def strip_optional_fields(cls, value: Optional[str], info) -> Optional[str]:
        return _strip_optional_text(value, info.field_name)


class ExamOut(BaseModel):
    id: int
    course_id: int
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
    course_id: int = Field(gt=0)

    @field_validator("subject")
    @classmethod
    def strip_subject(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class SessionOut(BaseModel):
    id: int
    course_id: int
    duration_seconds: int
    mode: str
    subject: Optional[str]
    completed_at: str

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    hours_studied: float
    session_count: int
    day_streak: int
    course_name: str


# ---- Notes ----

class NoteCreate(BaseModel):
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return _strip_required_text(value, "text")


class NoteOut(BaseModel):
    id: int
    text: str
    created_at: str

    model_config = {"from_attributes": True}


# ---- Study Progress ----

class ProgressUpdate(BaseModel):
    progress_pct: int = Field(ge=0, le=100)
    course_id: int = Field(gt=0)


class ProgressOut(BaseModel):
    id: int
    course_id: int
    subject: str
    progress_pct: int
    updated_at: str

    model_config = {"from_attributes": True}


# ---- Files ----

FileSection = Literal["lecture_notes", "past_exams", "formula_sheets", "practice"]


class UploadedFileOut(BaseModel):
    id: int
    course_id: int
    section: FileSection
    filename: str
    file_type: str
    uploaded_at: str

    model_config = {"from_attributes": True}


# ---- Videos ----

class VideoCreate(BaseModel):
    url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    thumbnail_url: Optional[str] = None
    course_id: int = Field(gt=0)

    @field_validator("url", "title")
    @classmethod
    def strip_required_values(cls, value: str, info) -> str:
        return _strip_required_text(value, info.field_name)

    @field_validator("thumbnail_url")
    @classmethod
    def strip_thumbnail_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class PlaylistImportRequest(BaseModel):
    playlist_url: str = Field(min_length=1)
    course_id: int = Field(gt=0)

    @field_validator("playlist_url")
    @classmethod
    def strip_playlist_url(cls, value: str) -> str:
        return _strip_required_text(value, "playlist_url")


class VideoOut(BaseModel):
    id: int
    course_id: int
    url: str
    title: str
    thumbnail_url: Optional[str]
    added_at: str

    model_config = {"from_attributes": True}


# ---- Questions ----

QuestionType = Literal["mcq", "free_text"]


class QuestionCreate(BaseModel):
    text: str = Field(min_length=1)
    question_type: QuestionType
    options: Optional[list[str]] = None
    correct_index: Optional[int] = None
    course_id: int = Field(gt=0)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return _strip_required_text(value, "text")

    @model_validator(mode="after")
    def validate_shape(self):
        if self.question_type == "mcq":
            if self.options is None or not 2 <= len(self.options) <= 4:
                raise ValueError("MCQ questions require 2 to 4 options")

            cleaned_options = [option.strip() for option in self.options]
            if any(not option for option in cleaned_options):
                raise ValueError("MCQ options must be non-empty strings")

            if self.correct_index is None or not 0 <= self.correct_index < len(cleaned_options):
                raise ValueError("correct_index must reference a valid option")

            self.options = cleaned_options
            return self

        self.options = None
        self.correct_index = None
        return self


class QuestionOut(BaseModel):
    id: int
    course_id: int
    text: str
    question_type: QuestionType
    options: Optional[list[str]]
    correct_index: Optional[int]
    created_at: str


# ---- Flashcards ----

class FlashcardCreate(BaseModel):
    front: str = Field(min_length=1)
    back: str = Field(min_length=1)
    course_id: int = Field(gt=0)

    @field_validator("front", "back")
    @classmethod
    def strip_required_values(cls, value: str, info) -> str:
        return _strip_required_text(value, info.field_name)


class FlashcardUpdate(BaseModel):
    front: Optional[str] = None
    back: Optional[str] = None

    @field_validator("front", "back")
    @classmethod
    def strip_optional_values(cls, value: Optional[str], info) -> Optional[str]:
        return _strip_optional_text(value, info.field_name)


class FlashcardOut(BaseModel):
    id: int
    course_id: int
    front: str
    back: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ---- Invite Tokens ----

class InviteOut(BaseModel):
    token: str
    url: str


class JoinRequest(BaseModel):
    token: str = Field(min_length=1)
    name: str = Field(min_length=1)

    @field_validator("token", "name")
    @classmethod
    def strip_required_values(cls, value: str, info) -> str:
        return _strip_required_text(value, info.field_name)


# ---- AI ----

FlashcardSource = Literal["notes", "uploaded_files", "both"]


class AIGenerateFlashcardsRequest(BaseModel):
    course_id: int = Field(gt=0)
    api_key: Optional[str] = None
    source: FlashcardSource = "both"

    @field_validator("api_key")
    @classmethod
    def strip_api_key(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class GeneratedFlashcard(BaseModel):
    front: str
    back: str

    @field_validator("front", "back")
    @classmethod
    def strip_generated_values(cls, value: str, info) -> str:
        return _strip_required_text(value, info.field_name)


# ---- Study Group ----

class GroupMemberCreate(BaseModel):
    name: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return _strip_required_text(value, "name")


class GroupMemberUpdate(BaseModel):
    is_online: bool


class GroupMemberOut(BaseModel):
    id: int
    name: str
    is_online: bool
    hours_this_week: float
    current_streak: int
    joined_at: str

    model_config = {"from_attributes": True}


class GroupMessageCreate(BaseModel):
    member_id: int
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def strip_message_text(cls, value: str) -> str:
        return _strip_required_text(value, "text")


class GroupMessageOut(BaseModel):
    id: int
    member_id: int
    author_name: str
    text: str
    created_at: str

    model_config = {"from_attributes": True}
