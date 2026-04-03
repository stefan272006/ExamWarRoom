from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text

from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    name = Column(String, nullable=False)
    created_at = Column(String, nullable=False)


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    exam_date = Column(String, nullable=False)
    created_at = Column(String, nullable=False)


class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
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
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    subject = Column(String, nullable=False)
    progress_pct = Column(Integer, nullable=False, default=0)
    updated_at = Column(String, nullable=False)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    section = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    stored_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    uploaded_at = Column(String, nullable=False)


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    thumbnail_url = Column(Text, nullable=True)
    added_at = Column(String, nullable=False)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    text = Column(Text, nullable=False)
    question_type = Column(String, nullable=False)
    options = Column(Text, nullable=True)
    correct_index = Column(Integer, nullable=True)
    created_at = Column(String, nullable=False)


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    name = Column(String, nullable=False)
    is_online = Column(Integer, nullable=False, default=0)
    hours_this_week = Column(Float, nullable=False, default=0.0)
    current_streak = Column(Integer, nullable=False, default=0)
    joined_at = Column(String, nullable=False)


class GroupMessage(Base):
    __tablename__ = "group_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    member_id = Column(Integer, ForeignKey("group_members.id"), nullable=False)
    author_name = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(String, nullable=False)


class InviteToken(Base):
    __tablename__ = "invite_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, nullable=False, unique=True)
    created_at = Column(String, nullable=False)
    used = Column(Integer, nullable=False, default=0)
