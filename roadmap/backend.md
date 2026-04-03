# Backend Roadmap

## Overview
Python + FastAPI server with SQLite database. Serves the static frontend and exposes a JSON API under `/api/`. All resource tables carry a `course_id` foreign key; all list endpoints filter by it. Study Group is the only resource shared across courses.

## Database Schema

All tables include `user_id INTEGER DEFAULT 1` for future auth support.

---

### courses *(new)*
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| name | TEXT | not null, unique per user |
| created_at | TEXT | ISO-8601 |

**Seed data** (inserted on first startup if table is empty):
```
EECS 2001
MATH 2030
MATH 1090
```

---

### exams
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| course_id | INTEGER | FK → courses.id, not null |
| name | TEXT | not null |
| subject | TEXT | not null |
| exam_date | TEXT | ISO-8601 datetime |
| created_at | TEXT | auto-set |

---

### focus_sessions
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| course_id | INTEGER | FK → courses.id, not null |
| duration_seconds | INTEGER | exact elapsed seconds, not null |
| mode | TEXT | "pomodoro", "short_break", "long_break", "deep_focus" |
| subject | TEXT | nullable |
| completed_at | TEXT | ISO-8601 timestamp |

**Hours math:** `hours_studied = SUM(duration_seconds) / 3600.0` — stored as exact seconds, converted to float on read. A 30-minute session = `duration_seconds=1800` → `0.5 hours`.

---

### notes
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| text | TEXT | not null |
| created_at | TEXT | auto-set |

*(Notes are not course-scoped — they are global quick-capture)*

---

### study_progress
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| course_id | INTEGER | FK → courses.id, not null |
| subject | TEXT | not null |
| progress_pct | INTEGER | 0-100 |
| updated_at | TEXT | auto-set |

Unique constraint: `(user_id, course_id, subject)`.

---

### uploaded_files
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| course_id | INTEGER | FK → courses.id, not null |
| section | TEXT | "lecture_notes", "past_exams", "formula_sheets", "practice" |
| filename | TEXT | original filename |
| stored_name | TEXT | UUID-based filename on disk |
| file_type | TEXT | "PDF", "PNG", "JPG", "WEBP", "DOCX" |
| uploaded_at | TEXT | ISO-8601 |

Files saved to `static/uploads/<section>/`.

---

### videos
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| course_id | INTEGER | FK → courses.id, not null |
| url | TEXT | full YouTube watch URL |
| title | TEXT | from noembed or yt-dlp |
| thumbnail_url | TEXT | nullable |
| added_at | TEXT | ISO-8601 |

---

### questions
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| course_id | INTEGER | FK → courses.id, not null |
| text | TEXT | not null |
| question_type | TEXT | "mcq" or "free_text" |
| options | TEXT | JSON array (MCQ only, else null) |
| correct_index | INTEGER | 0-based (MCQ only, else null) |
| created_at | TEXT | ISO-8601 |

---

### flashcards *(new)*
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| course_id | INTEGER | FK → courses.id, not null |
| front | TEXT | question / term, not null |
| back | TEXT | answer / definition, not null |
| created_at | TEXT | ISO-8601 |
| updated_at | TEXT | ISO-8601, auto-set on update |

---

### group_members
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| name | TEXT | not null |
| is_online | INTEGER | 0 or 1, default 0 |
| hours_this_week | REAL | default 0.0 |
| current_streak | INTEGER | default 0 |
| joined_at | TEXT | ISO-8601 |

*(No course_id — study group is shared)*

---

### group_messages
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| user_id | INTEGER | default 1 |
| member_id | INTEGER | FK → group_members.id |
| author_name | TEXT | denormalized |
| text | TEXT | not null |
| created_at | TEXT | ISO-8601 |

---

### invite_tokens *(new — Phase 3)*
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| token | TEXT | unique, 8-char UUID prefix |
| created_at | TEXT | ISO-8601 |
| used | INTEGER | 0 or 1, default 0 |

Single-use invite tokens for the study group. No `user_id` — tokens are global.

---

## API Endpoints

### Courses *(new)*
| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | /api/courses | — | Course[] |
| POST | /api/courses | {name} | Course (201) |
| DELETE | /api/courses/{id} | — | 204 |

No seed data. Courses table starts empty; users add their own courses via `POST /api/courses`.

---

### Exams
All endpoints require `course_id` (query param for GET/DELETE, body field for POST/PUT).

| Method | Path | Query / Body | Response |
|--------|------|------|----------|
| GET | /api/exams | `?course_id=` | Exam[] (asc by date) |
| POST | /api/exams | `{name, subject, exam_date, course_id}` | Exam (201) |
| PUT | /api/exams/{id} | `{name?, subject?, exam_date?}` | Exam |
| DELETE | /api/exams/{id} | — | 204 |

POST also auto-creates a `study_progress` entry at 0% for `(course_id, subject)` if it doesn't exist.

---

### Focus Sessions
| Method | Path | Query / Body | Response |
|--------|------|------|----------|
| POST | /api/sessions | `{duration_seconds, mode, subject?, course_id}` | Session (201) |
| GET | /api/sessions/stats | `?course_id=` | `{hours_studied, session_count, day_streak, course_name}` |

Stats logic (all filtered by `course_id`):
- **hours_studied**: `ROUND(SUM(duration_seconds) / 3600.0, 2)` — returns float
- **session_count**: `COUNT(*)`
- **day_streak**: walk backwards from today counting distinct dates in `completed_at`
- **course_name**: joined from `courses` table for display label

---

### Notes
*(No course scoping)*
| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | /api/notes | — | Note[] (newest first) |
| POST | /api/notes | {text} | Note (201) |
| DELETE | /api/notes/{id} | — | 204 |

---

### Study Progress
| Method | Path | Query / Body | Response |
|--------|------|------|----------|
| GET | /api/progress | `?course_id=` | Progress[] |
| PUT | /api/progress/{subject} | `{progress_pct, course_id}` | Progress (upsert) |

---

### Files
| Method | Path | Query / Body | Response |
|--------|------|------|----------|
| GET | /api/files | `?section=&course_id=` | File[] |
| POST | /api/files/upload | multipart: `file`, `section`, `course_id` | File (201) |
| GET | /api/files/{id}/content | `?section=` | raw file (correct Content-Type) |
| DELETE | /api/files/{id} | — | 204 + delete from filesystem |

Upload logic:
- Validate extension against allowlist: `.pdf`, `.png`, `.jpg`, `.webp`, `.docx`
- UUID-based `stored_name` to prevent path traversal
- Save to `static/uploads/<section>/`

---

### Videos
| Method | Path | Query / Body | Response |
|--------|------|------|----------|
| GET | /api/videos | `?course_id=` | Video[] (newest first) |
| POST | /api/videos | `{url, title, thumbnail_url, course_id}` | Video (201) |
| DELETE | /api/videos/{id} | — | 204 |
| POST | /api/videos/import-playlist | `{playlist_url, course_id}` | Video[] (201) |

Playlist import: `yt-dlp --flat-playlist --dump-json`; skip duplicates by `(url, course_id)`.

---

### Questions
| Method | Path | Query / Body | Response |
|--------|------|------|----------|
| GET | /api/questions | `?course_id=` | Question[] (newest first) |
| POST | /api/questions | `{text, question_type, options?, correct_index?, course_id}` | Question (201) |
| DELETE | /api/questions/{id} | — | 204 |

Validation: if `mcq`, options must be 2–4 strings; `correct_index` must be valid. Options stored as JSON string.

---

### Flashcards *(new)*
| Method | Path | Query / Body | Response |
|--------|------|------|----------|
| GET | /api/flashcards | `?course_id=` | Flashcard[] (newest first) |
| POST | /api/flashcards | `{front, back, course_id}` | Flashcard (201) |
| PUT | /api/flashcards/{id} | `{front?, back?}` | Flashcard |
| DELETE | /api/flashcards/{id} | — | 204 |

---

### Study Group — Members
*(No course scoping)*
| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | /api/group/members | — | Member[] |
| POST | /api/group/members | {name} | Member (201) |
| PUT | /api/group/members/{id} | {is_online} | Member |

### Study Group — Messages
*(No course scoping)*
| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | /api/group/messages | — | Message[] (oldest first, last 100) |
| POST | /api/group/messages | {member_id, text} | Message (201) |
| DELETE | /api/group/messages/{id} | — | 204 |

### Study Group — Invite Links *(new — Phase 3)*
*(No course scoping)*
| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | /api/group/invite | — | `{token, url}` (201) |
| POST | /api/group/join | `{token, name}` | Member (201) |

`POST /api/group/invite`: generates a short UUID token (8 chars), stores in `invite_tokens`, returns `{ token, url }` where `url = "{base_url}/?join={token}"`.

`POST /api/group/join`: validates token exists and `used=0`, creates `GroupMember`, sets `invite_tokens.used=1`. Returns 404 if token invalid or already used.

---

### AI Flashcard Generation *(new — Phase 3)*
| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | /api/ai/generate-flashcards | `{course_id, api_key, source}` | `[{front, back}]` (200) |

**Body fields:**
- `course_id`: integer — which course to pull PDFs from
- `api_key`: string — user's Anthropic API key (never stored server-side)
- `source`: `"notes"` \| `"uploaded_files"` \| `"both"` (default `"both"`)

**Logic:**
- If `source` includes `"notes"`: fetch all `Note` rows for `user_id=1`; join as text
- If `source` includes `"uploaded_files"`: find PDF `UploadedFile` rows for the course (cap at 3); extract text from first 5 pages via PyMuPDF (`fitz`); cap each file at 3000 chars
- Combine content (max 6000 chars total sent to LLM)
- Call `anthropic.Anthropic(api_key=...).messages.create(model="claude-haiku-4-5-20251001", ...)` with a prompt requesting exactly 5 flashcards as a JSON array `[{front, back}]`
- Parse JSON array from response; return filtered list of non-empty cards
- **Errors**: 400 if no api_key; 401 if Anthropic `AuthenticationError`; 422 if no content found; 502 for other LLM failures

**Key decision**: API key passed per-request and never persisted server-side — user stores it in localStorage client-side.

---

## Implementation Steps

**Phase 1 (existing):**
- [ ] `app/database.py` — engine, SessionLocal, Base, get_db
- [ ] `app/models.py` — all ORM models (including `Course`, `Flashcard`; add `course_id` FK to all scoped tables)
- [ ] `app/schemas.py` — Pydantic models for all resources
- [ ] `app/routers/exams.py` — CRUD + course_id filter + auto-create progress
- [ ] `app/routers/sessions.py` — POST + GET stats with course_id filter and float hours
- [ ] `app/routers/notes.py` — GET, POST, DELETE
- [ ] `app/routers/progress.py` — GET + PUT upsert (course_id scoped)
- [ ] `app/main.py` — app, routers, CORS, static mount, create tables on startup, seed courses

**Phase 2 (existing):**
- [ ] `app/routers/courses.py` — GET, POST, DELETE + seed on startup
- [ ] `app/routers/files.py` — upload (UUID rename, ext allowlist), list, serve, delete (all course_id scoped)
- [ ] `app/routers/videos.py` — CRUD + playlist import via yt-dlp (course_id scoped)
- [ ] `app/routers/questions.py` — CRUD with MCQ validation (course_id scoped)
- [ ] `app/routers/flashcards.py` — GET, POST, PUT, DELETE (course_id scoped)
- [ ] `app/routers/group.py` — members + messages (no course scoping)
- [ ] `app/main.py` — register new routers; create `static/uploads/{section}/` dirs on startup
- [ ] `requirements.txt` — fastapi, uvicorn, sqlalchemy, pydantic, python-multipart, yt-dlp

**Phase 3 (new):**
- [ ] `app/models.py` — add `InviteToken` model (`invite_tokens` table)
- [ ] `app/schemas.py` — add `InviteOut`, `JoinRequest` Pydantic schemas
- [ ] `app/routers/group.py` — add `POST /invite` and `POST /join` endpoints; import `uuid`, `Request`, `InviteToken`
- [ ] `app/routers/ai.py` — new file; `POST /ai/generate-flashcards`; reads notes + PDFs; calls Anthropic API
- [ ] `app/main.py` — import and register `ai` router with `prefix="/api"`
- [ ] `requirements.txt` — add `anthropic>=0.25`, `pymupdf>=1.24`

---

## Verification
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Courses (user-created, starts empty)
curl http://localhost:8000/api/courses
# → []
curl -X POST http://localhost:8000/api/courses \
  -H 'Content-Type: application/json' \
  -d '{"name":"EECS 2001"}'
# → {"id":1,"name":"EECS 2001",...}

# Exams (course-scoped)
curl "http://localhost:8000/api/exams?course_id=1"
curl -X POST http://localhost:8000/api/exams \
  -H 'Content-Type: application/json' \
  -d '{"name":"Midterm","subject":"Algorithms","exam_date":"2026-05-01T09:00:00","course_id":1}'

# Sessions — decimal hours
curl -X POST http://localhost:8000/api/sessions \
  -H 'Content-Type: application/json' \
  -d '{"duration_seconds":1800,"mode":"pomodoro","course_id":1}'
curl "http://localhost:8000/api/sessions/stats?course_id=1"
# → {"hours_studied": 0.5, "session_count": 1, "day_streak": 1, "course_name": "EECS 2001"}

# Flashcards
curl "http://localhost:8000/api/flashcards?course_id=1"
curl -X POST http://localhost:8000/api/flashcards \
  -H 'Content-Type: application/json' \
  -d '{"front":"What is Big-O?","back":"Upper bound on algorithm growth rate","course_id":1}'
curl -X PUT http://localhost:8000/api/flashcards/1 \
  -H 'Content-Type: application/json' \
  -d '{"back":"Asymptotic upper bound on time/space complexity"}'

# Files (course-scoped)
curl "http://localhost:8000/api/files?section=lecture_notes&course_id=1"
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@notes.pdf" -F "section=lecture_notes" -F "course_id=1"

# Videos (course-scoped)
curl "http://localhost:8000/api/videos?course_id=2"
curl -X POST http://localhost:8000/api/videos/import-playlist \
  -H 'Content-Type: application/json' \
  -d '{"playlist_url":"https://www.youtube.com/playlist?list=PLxxx","course_id":2}'
```

```bash
# Phase 3: Invite links
curl -X POST http://localhost:8000/api/group/invite
# → {"token":"a1b2c3d4","url":"http://localhost:8000/?join=a1b2c3d4"}

curl -X POST http://localhost:8000/api/group/join \
  -H 'Content-Type: application/json' \
  -d '{"token":"a1b2c3d4","name":"Alice"}'
# → {"id":1,"name":"Alice","is_online":false,"hours_this_week":0.0,"current_streak":0,"joined_at":"..."}

# Second use of same token:
curl -X POST http://localhost:8000/api/group/join \
  -H 'Content-Type: application/json' \
  -d '{"token":"a1b2c3d4","name":"Bob"}'
# → 404 {"detail":"Invalid or already-used invite token"}

# Phase 3: AI flashcard generation (requires valid Anthropic key)
curl -X POST http://localhost:8000/api/ai/generate-flashcards \
  -H 'Content-Type: application/json' \
  -d '{"course_id":1,"api_key":"sk-ant-...","source":"both"}'
# → [{"front":"...","back":"..."},...]
```

## Key Decisions
- All timestamps: ISO-8601 strings (not SQLAlchemy DateTime) for simple SQLite sorting
- `StaticFiles(html=True)` mount last in `main.py` so API routes take priority
- No Alembic — `create_all` on startup; courses table starts empty, user-populated
- `duration_seconds` stored as exact integer; float conversion only at read time
- `course_id` is required (not optional) on all scoped POST endpoints — frontend always sends it
- Files: UUID rename + extension allowlist prevents path traversal
- `yt-dlp` via subprocess for playlist extraction (no YouTube API key needed)
- MCQ `options` stored as JSON string in SQLite; deserialized in schema layer
- Group messages: `author_name` denormalized to avoid joins on every fetch
- Study Group intentionally not course-scoped — represents a real group of people across all courses
- Invite tokens are single-use (8-char UUID prefix); no expiry enforced at DB level — delete old rows manually if needed
- AI API key is never stored server-side — passed per-request from the frontend's localStorage
- PyMuPDF (`fitz`) used for PDF text extraction — cap at 3 files × 5 pages × 3000 chars to stay within LLM context limits
- `claude-haiku-4-5-20251001` used for generation (fast, cheap); prompt requests JSON array response only
