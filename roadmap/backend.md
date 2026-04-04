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
| progress_pct | INTEGER | legacy column, always written as 0; actual pct computed at read time |
| confidence | INTEGER | 0=Struggling, 1=Getting There, 2=Confident; default 0 |
| updated_at | TEXT | auto-set |

Unique constraint: `(user_id, course_id, subject)`.

**Migration:** `confidence` column added via `_add_column_if_missing` in `database.py` at startup — safe to run on existing databases. Existing rows get `confidence=0` (Struggling) as default.

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
| GET | /api/progress | `?course_id=` | Progress[] (with computed `progress_pct`) |
| POST | /api/progress | `{subject, course_id}` | Progress (201) — manual subject creation |
| PUT | /api/progress/{subject} | `{confidence, course_id}` | Progress (upsert) |
| DELETE | /api/progress/{subject} | `?course_id=` | 204 |

**`progress_pct` is computed at read time** — never stored. Formula:
- `confidence=0` (Struggling): base = 10
- `confidence=1` (Getting There): base = 45
- `confidence=2` (Confident): base = 80
- `activity_bonus` = `min(20, floor(hours_for_subject * 4))` — hours pulled from `focus_sessions` for matching `(course_id, subject)`
- `progress_pct` = `min(100, base + activity_bonus)`

GET endpoint runs a single grouped query (`GROUP BY subject`) on `focus_sessions` to get all hours at once, then builds each response dict via `_build_out()`.

POST returns 409 if subject already exists for the course. Creates row with `confidence=0`.

DELETE returns 404 if `(course_id, subject)` not found.

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
| POST | /api/ai/generate-flashcards | `{course_id, provider, api_key?, gemini_api_key?, file_id?, source?}` | `[{front, back}]` (200) |

**Body fields:**
- `course_id`: integer — which course to pull content from
- `provider`: `"anthropic"` \| `"gemini"` (default `"anthropic"`) — which LLM to use
- `api_key`: string (optional) — Anthropic API key; required when `provider="anthropic"`
- `gemini_api_key`: string (optional) — Google Gemini API key; required when `provider="gemini"` (free tier available at aistudio.google.com)
- `file_id`: integer (optional) — if provided, extract text from this specific `UploadedFile` only (ignores `source`)
- `source`: `"notes"` \| `"uploaded_files"` \| `"both"` (default `"both"`) — used only when `file_id` is absent

**Logic:**
**Content collection** (shared for both providers):
- If `file_id` is provided: look up that exact `UploadedFile` row (404 if not found or wrong course); extract text from it (PDF → PyMuPDF, max 5 pages × 3000 chars; `.txt`/`.docx` → read raw text, cap at 6000 chars); skip `source` logic entirely
- Else if `source` includes `"notes"`: fetch all `Note` rows for `user_id=1`; join as text
- Else if `source` includes `"uploaded_files"`: find PDF `UploadedFile` rows for the course (cap at 3 files); extract text from first 5 pages via PyMuPDF (`fitz`); cap each file at 3000 chars
- Combine content (max 6000 chars total sent to LLM)
- 422 if combined content is empty

**Anthropic path** (`provider="anthropic"`):
- SDK import guard: import `anthropic` with try/except; return 503 if not installed
- 400 if `api_key` missing; 401 if `AuthenticationError`; 402 if `BadRequestError` with credit/billing message
- Call `anthropic.Anthropic(api_key=api_key).messages.create(model="claude-haiku-4-5-20251001", max_tokens=1024, ...)`

**Gemini path** (`provider="gemini"`):
- SDK import guard: import `google.generativeai as genai` with try/except; return 503 if not installed
- 400 if `gemini_api_key` missing
- Call `genai.configure(api_key=gemini_api_key)` then `genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)`
- Error handling by inspecting `type(exc).__name__`: `PermissionDenied` → 401; `ResourceExhausted` → 429; other → 502

**Shared prompt**: "Generate exactly 10 study flashcards from the provided material. Return raw JSON only as an array of objects with keys front and back. Do not wrap the JSON in markdown fences."

**Errors (all providers)**:
- 400 — key missing
- 401 — invalid key
- 402 — Anthropic no credits (Anthropic only)
- 404 — `file_id` not found for course
- 422 — no content found
- 429 — Gemini quota exceeded (Gemini only)
- 502 — other LLM failure
- 503 — SDK not installed

**Key decision**: API keys passed per-request, never stored server-side. Both `anthropic` and `google-generativeai` packages listed in `requirements.txt`. Gemini Flash is free-tier accessible with no billing required.

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
- [ ] `app/routers/ai.py` — new file; `POST /ai/generate-flashcards`; handles `file_id` (single-file mode) or `source` (batch mode); calls Anthropic SDK directly (`anthropic.Anthropic(api_key=...)`) — no LangChain; guards import with try/except to return 503 instead of crashing
- [ ] `app/main.py` — import and register `ai` router with `prefix="/api"`
- [ ] `requirements.txt` — add `anthropic>=0.25`, `pymupdf>=1.24` (must be installed in the project virtualenv)

**Phase 4 (confidence progress + Gemini):**
- [ ] `app/database.py` — in `migrate_sqlite_schema`, add `_add_column_if_missing(connection, "study_progress", "confidence INTEGER DEFAULT 0")` after the existing rebuild checks; the helper is already idempotent via `PRAGMA table_info`
- [ ] `app/models.py` — add `confidence = Column(Integer, nullable=False, default=0)` to `StudyProgress` after `progress_pct`; keep `progress_pct` for `create_all` NOT NULL compatibility (always written as 0, overridden at read time)
- [ ] `app/schemas.py`:
  - Replace `ProgressUpdate` body: `confidence: int = Field(ge=0, le=2)` + `course_id`; remove `progress_pct`
  - Add `confidence: int` field to `ProgressOut`; keep `progress_pct` (computed at API layer, not from DB)
  - Add new `ProgressCreate` schema: `subject: str`, `course_id: int`
  - Extend `AIGenerateFlashcardsRequest`: add `provider: Literal["anthropic","gemini"] = "anthropic"` and `gemini_api_key: Optional[str] = None`; rename existing `api_key` validator to handle both key fields
- [ ] `app/routers/progress.py` — full rewrite:
  - Add `CONFIDENCE_BASE = {0: 10, 1: 45, 2: 80}` constant
  - `_get_hours_by_subject(db, course_id)` — single `GROUP BY subject` query on `FocusSession`; returns `{subject: hours_float}`
  - `_build_out(p, hours_by_subject)` — computes `progress_pct = min(100, base + min(20, int(hours*4)))` from `CONFIDENCE_BASE[p.confidence]`; returns plain dict matching `ProgressOut`
  - `GET /api/progress` — query all rows for course, call `_get_hours_by_subject` once, map with `_build_out`
  - `PUT /api/progress/{subject}` — upsert by `(course_id, subject)`; write `confidence=data.confidence`, `progress_pct=0`; return `_build_out`
  - `DELETE /api/progress/{subject}?course_id=` — 404 if not found, else `db.delete` + commit, 204
  - `POST /api/progress` — body `ProgressCreate`; 409 if row already exists; create with `confidence=0, progress_pct=0`; return 201 with `_build_out`
- [ ] `app/routers/ai.py` — add Gemini branch alongside existing Anthropic path:
  - Import `google.generativeai as genai` with try/except; set `GENAI_IMPORT_ERROR` accordingly
  - `_handle_gemini_error(exc)` — inspect `type(exc).__name__`: `PermissionDenied` → 401, `ResourceExhausted` → 429, else 502
  - `_generate_with_gemini(api_key, prompt)` — `genai.configure(api_key=...)`, `genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)`, parse cards via existing `_extract_json_array`
  - In `generate_flashcards` endpoint: after prompt assembly, branch on `data.provider`; Gemini path calls `_generate_with_gemini`; Anthropic path unchanged
- [ ] `requirements.txt` — append `google-generativeai>=0.8`; install with `pip3.12 install google-generativeai` to match the uvicorn Python version

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

```bash
# Phase 4: Confidence-based progress

# Manual subject creation
curl -X POST http://localhost:8000/api/progress \
  -H 'Content-Type: application/json' \
  -d '{"subject":"Graph Theory","course_id":1}'
# → {"id":3,"course_id":1,"subject":"Graph Theory","confidence":0,"progress_pct":10,"updated_at":"..."}

# Duplicate subject → 409
curl -X POST http://localhost:8000/api/progress \
  -H 'Content-Type: application/json' \
  -d '{"subject":"Graph Theory","course_id":1}'
# → 409 {"detail":"Subject already exists for this course"}

# Cycle confidence to "Getting There"
curl -X PUT "http://localhost:8000/api/progress/Graph%20Theory" \
  -H 'Content-Type: application/json' \
  -d '{"confidence":1,"course_id":1}'
# → {"id":3,"course_id":1,"subject":"Graph Theory","confidence":1,"progress_pct":45,"updated_at":"..."}

# After logging a 2h focus session for "Graph Theory" (2h × 4 = 8 bonus pts):
curl "http://localhost:8000/api/progress?course_id=1"
# → [...{"subject":"Graph Theory","confidence":1,"progress_pct":53}...]
# (45 base + 8 activity bonus = 53)

# Cycle to "Confident"
curl -X PUT "http://localhost:8000/api/progress/Graph%20Theory" \
  -H 'Content-Type: application/json' \
  -d '{"confidence":2,"course_id":1}'
# → {"confidence":2,"progress_pct":88,...}
# (80 base + 8 activity bonus = 88)

# Delete subject
curl -X DELETE "http://localhost:8000/api/progress/Graph%20Theory?course_id=1"
# → 204

# Delete non-existent subject → 404
curl -X DELETE "http://localhost:8000/api/progress/Nonexistent?course_id=1"
# → 404 {"detail":"Subject not found for this course"}

# Phase 4: Gemini flashcard generation (free tier, no billing required)
curl -X POST http://localhost:8000/api/ai/generate-flashcards \
  -H 'Content-Type: application/json' \
  -d '{"course_id":1,"provider":"gemini","gemini_api_key":"AIza...","source":"both"}'
# → [{"front":"...","back":"..."},...]

# Gemini with invalid key → 401
curl -X POST http://localhost:8000/api/ai/generate-flashcards \
  -H 'Content-Type: application/json' \
  -d '{"course_id":1,"provider":"gemini","gemini_api_key":"bad-key","source":"both"}'
# → 401 {"detail":"Invalid Gemini API key"}
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
- `claude-haiku-4-5-20251001` used for generation (fast, cheap); prompt requests JSON array response only — no markdown fences
- `anthropic` SDK imported with try/except at module top; endpoint returns 503 if not installed (never crashes the whole app at startup)
- `file_id` in the generate request takes priority over `source` — enables single-file targeting from the frontend file selector
- **Confidence formula**: `progress_pct = min(100, CONFIDENCE_BASE[confidence] + min(20, floor(hours*4)))` — confidence drives the bulk of the score (10/45/80%) so it can't be gamed purely by logging study time; the activity bonus (max +20%) makes the bar visibly move as you study, keeping it motivational without inflating scores dishonestly. The `progress_pct` column in SQLite is always written as 0; the computed value is never persisted — this avoids stale data if the formula changes.
- **Gemini chosen over Groq/rule-based**: Gemini Flash has a genuine free tier with no credit card required (rate-limited, not pay-per-token at low usage); Groq also has a free tier but Gemini's context window and reliability are better for document-based generation. Rule-based generation (keyword extraction) was rejected because the output quality is too poor to be useful for studying.
- **`google-generativeai` SDK error handling**: Gemini SDK exceptions are caught by `type(exc).__name__` string comparison rather than importing `google.api_core.exceptions` — avoids a second import-guard block; the approach is fragile only if Google renames exception classes, which is rare and immediately visible in tests.
