from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401
from app.database import Base, engine, migrate_sqlite_schema
from app.routers import ai, courses, exams, files, flashcards, group, notes, progress, questions, sessions, videos

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
UPLOAD_SECTIONS = (
    "lecture_notes",
    "past_exams",
    "formula_sheets",
    "practice",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    for section in UPLOAD_SECTIONS:
        (UPLOAD_DIR / section).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema(engine)
    yield


app = FastAPI(title="Exam War Room", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(exams.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(progress.router, prefix="/api")
app.include_router(courses.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(questions.router, prefix="/api")
app.include_router(flashcards.router, prefix="/api")
app.include_router(group.router, prefix="/api")
app.include_router(ai.router, prefix="/api")

app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
