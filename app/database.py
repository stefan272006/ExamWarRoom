from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{ROOT_DIR / 'warroom.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def _get_column_names(connection, table_name: str) -> set[str]:
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
    return {row["name"] for row in rows}


def _add_column_if_missing(connection, table_name: str, column_definition: str) -> None:
    column_name = column_definition.split()[0]
    if column_name not in _get_column_names(connection, table_name):
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}"))


def _rebuild_study_progress_table(connection) -> None:
    connection.execute(text("ALTER TABLE study_progress RENAME TO study_progress_legacy"))
    connection.execute(
        text(
            """
            CREATE TABLE study_progress (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                course_id INTEGER,
                subject VARCHAR NOT NULL,
                progress_pct INTEGER NOT NULL DEFAULT 0,
                updated_at VARCHAR NOT NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO study_progress (id, user_id, subject, progress_pct, updated_at)
            SELECT id, user_id, subject, progress_pct, updated_at
            FROM study_progress_legacy
            """
        )
    )
    connection.execute(text("DROP TABLE study_progress_legacy"))


def _rebuild_videos_table(connection) -> None:
    connection.execute(text("ALTER TABLE videos RENAME TO videos_legacy"))
    connection.execute(
        text(
            """
            CREATE TABLE videos (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                course_id INTEGER,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                thumbnail_url TEXT,
                added_at VARCHAR NOT NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO videos (id, user_id, url, title, thumbnail_url, added_at)
            SELECT id, user_id, url, title, thumbnail_url, added_at
            FROM videos_legacy
            """
        )
    )
    connection.execute(text("DROP TABLE videos_legacy"))


def migrate_sqlite_schema(bind=engine) -> None:
    if bind.dialect.name != "sqlite":
        return

    with bind.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())

        if "study_progress" in table_names and "course_id" not in _get_column_names(connection, "study_progress"):
            _rebuild_study_progress_table(connection)

        if "videos" in table_names and "course_id" not in _get_column_names(connection, "videos"):
            _rebuild_videos_table(connection)

        table_names = set(inspect(connection).get_table_names())
        for table_name in ("exams", "focus_sessions", "uploaded_files", "questions"):
            if table_name in table_names:
                _add_column_if_missing(connection, table_name, "course_id INTEGER")

        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_courses_user_name
                ON courses (user_id, name)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_study_progress_user_course_subject
                ON study_progress (user_id, course_id, subject)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_videos_user_course_url
                ON videos (user_id, course_id, url)
                """
            )
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
