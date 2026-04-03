# Backend Roadmap

## Overview
Python + FastAPI server with SQLite database. Serves the static frontend and exposes a JSON API under `/api/`.

## Database Schema

All tables include `user_id INTEGER DEFAULT 1` for future auth support.

### exams
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| name | TEXT | not null |
| subject | TEXT | not null |
| exam_date | TEXT | ISO-8601 datetime |
| created_at | TEXT | auto-set on creation |

### focus_sessions
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| duration_seconds | INTEGER | not null |
| mode | TEXT | "pomodoro", "short_break", "long_break", "deep_focus" |
| subject | TEXT | nullable, optional tag |
| completed_at | TEXT | ISO-8601 timestamp |

### notes
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| text | TEXT | not null |
| created_at | TEXT | auto-set on creation |

### study_progress
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| subject | TEXT | not null, unique |
| progress_pct | INTEGER | 0-100 |
| updated_at | TEXT | auto-set on update |

## API Endpoints

### Exams
| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | /api/exams | — | Exam[] (ordered by date asc) |
| POST | /api/exams | {name, subject, exam_date} | Exam (201) |
| PUT | /api/exams/{id} | {name?, subject?, exam_date?} | Exam |
| DELETE | /api/exams/{id} | — | 204 |

POST also auto-creates a study_progress entry at 0% if the subject is new.

### Focus Sessions
| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | /api/sessions | {duration_seconds, mode, subject?} | Session (201) |
| GET | /api/sessions/stats | — | {hours_studied, session_count, day_streak} |

Stats logic:
- **hours_studied**: SUM(duration_seconds) / 3600
- **session_count**: COUNT(*)
- **day_streak**: Walk backwards from today counting distinct dates in completed_at

### Notes
| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | /api/notes | — | Note[] (newest first) |
| POST | /api/notes | {text} | Note (201) |
| DELETE | /api/notes/{id} | — | 204 |

### Study Progress
| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | /api/progress | — | Progress[] |
| PUT | /api/progress/{subject} | {progress_pct} | Progress (upsert) |

## Implementation Steps

- [ ] `app/database.py` — SQLAlchemy engine, SessionLocal, Base, get_db
- [ ] `app/models.py` — 4 ORM models
- [ ] `app/schemas.py` — Pydantic request/response models
- [ ] `app/routers/exams.py` — CRUD + auto-create progress
- [ ] `app/routers/sessions.py` — POST session + GET stats with streak calc
- [ ] `app/routers/notes.py` — GET, POST, DELETE
- [ ] `app/routers/progress.py` — GET list + PUT upsert
- [ ] `app/main.py` — FastAPI app, include routers, CORS, mount static/, create tables on startup
- [ ] `requirements.txt` — fastapi, uvicorn, sqlalchemy, pydantic
- [ ] Copy `front.html` to `static/index.html`

## Verification
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Test endpoints
curl http://localhost:8000/api/exams                    # → []
curl -X POST http://localhost:8000/api/exams \
  -H 'Content-Type: application/json' \
  -d '{"name":"Linear Algebra","subject":"Math","exam_date":"2026-04-10T09:00:00"}'
curl http://localhost:8000/api/exams                    # → [exam object]
curl http://localhost:8000/api/sessions/stats           # → {hours_studied: 0, ...}
curl http://localhost:8000/api/notes                    # → []
curl http://localhost:8000/api/progress                 # → [{subject: "Math", ...}]
```

## Key Decisions
- All timestamps stored as ISO-8601 strings (not SQLAlchemy DateTime) for simple SQLite sorting
- `StaticFiles(html=True)` mount must come LAST in main.py so API routes take priority
- No Alembic migrations — `create_all` on startup is sufficient for this scale
- CORS middleware included for development flexibility
