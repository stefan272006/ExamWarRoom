# Exam War Room

Student exam preparation dashboard — a full-stack web app with a dark command-center aesthetic.

## Tech Stack
- **Backend**: Python + FastAPI + SQLAlchemy + SQLite
- **Frontend**: Vanilla HTML/CSS/JS (no framework, no build step)
- **Fonts**: DM Serif Text, JetBrains Mono, Libre Franklin (loaded from Google Fonts)

## Project Layout
- `app/` — FastAPI backend (main.py, database.py, models.py, schemas.py, routers/)
- `static/index.html` — The entire frontend in one file
- `front.html` — Original static prototype (kept for reference)
- `warroom.db` — SQLite database (auto-created on first run, do not commit)
- `requirements.txt` — Python dependencies

## Running
```
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000

## API Convention
- All endpoints under `/api/` prefix
- JSON request/response
- Routers: exams, sessions, notes, progress
- `user_id` column exists on all tables (defaults to 1) for future auth support

## Design Principles
- Dark utilitarian aesthetic — amber accents on matte black
- Keep frontend as a single HTML file — no framework, no build step
- Forms reuse existing `.note-input` and `.btn` CSS classes
- Flashcards are client-side only (no backend)
- SQLite with no migrations — tables auto-created via `Base.metadata.create_all`

## Roadmap
Implementation is split into two independent phases. See `roadmap/` for details:
- [`roadmap/backend.md`](roadmap/backend.md) — FastAPI server, database, API endpoints
- [`roadmap/frontend.md`](roadmap/frontend.md) — Wire static HTML to the backend API