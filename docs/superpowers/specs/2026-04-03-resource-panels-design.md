# Resource Panels — Design Spec
**Date:** 2026-04-03

## Overview
Expand the Exam War Room dashboard with a persistent left sidebar and six functional resource panels that open as right-side drawers alongside the existing dashboard. All panels share the existing dark/amber aesthetic.

---

## Layout & Navigation

### Top Bar
- Unchanged (War Room logo, status dot, clock)
- Gains a persistent **timer widget** on the right: `25:00 · Pomodoro` in amber monospace, always visible regardless of which panel is open

### Left Sidebar
- Fixed, ~220px wide
- Background: `--surface` with a 1px right border using `--amber-dim`
- Contains the 6 resource buttons stacked vertically, each with:
  - Icon (existing unicode glyphs)
  - Name (e.g. "Lecture Notes")
  - Subtext count (e.g. "24 files") in dim monospace
- **Active state**: amber left-border accent + amber text
- **Hover state**: `--amber-glow` background

### Main Content Area
- Existing dashboard grid shifts right to fill remaining space (minus sidebar width)
- When a drawer is open, the grid compresses to fit the remaining width

### Right Drawer
- Slides in from the right, ~420px wide
- Has a header with section title + close (×) button
- Dismissing the drawer restores full grid width
- One drawer open at a time (opening a new one closes the current)

---

## Panel 1: File Panels (Lecture Notes, Past Exams, Formula Sheets)

All three share identical UI structure.

### Drawer Contents
- **Header**: Section title + file count badge + "Upload" button (amber)
- **Upload zone**: Drag-and-drop area with dashed amber border; "Drop files here or click to browse"; accepts PDF, images, common doc formats
- **File list**: Each file shows filename, file type tag (`PDF`, `PNG`, etc.), upload date (dim monospace), delete (×) on hover
- **Inline preview**: Clicking a file expands a preview pane — PDFs via native `<iframe>`, images displayed inline; "Close Preview" collapses it

### Backend
- Files stored at `static/uploads/{section}/` on the server filesystem
- New `/api/files` router:
  - `POST /api/files/upload?section=lecture_notes` — multipart file upload
  - `GET /api/files?section=lecture_notes` — list files
  - `DELETE /api/files/{filename}?section=lecture_notes` — delete file
  - Files served statically from `static/uploads/`
- New `files` table: `id`, `section`, `filename`, `original_name`, `uploaded_at`, `user_id`

---

## Panel 2: Video Lectures

### Drawer Contents
- **Header**: "Video Lectures" + video count badge
- **Add video**: Two input rows:
  - Single URL: text input + "Add" button
  - Playlist URL: text input + "Import" button (fetches via noembed.com — no API key required)
- **Video list**: Each entry shows thumbnail, title, play (▶) and delete (×) on hover

### Player
- Clicking a video opens an embedded `<iframe>` YouTube player in the **main content area** (replaces dashboard grid)
- Right drawer stays open showing the video list for easy switching
- Top-bar timer remains visible throughout
- A "Back to Dashboard" button returns to the grid view

### Backend
- New `videos` table: `id`, `youtube_url`, `title`, `thumbnail_url`, `created_at`, `user_id`
- New `/api/videos` router:
  - `GET /api/videos` — list all
  - `POST /api/videos` — add single video (fetches title/thumbnail via noembed.com)
  - `POST /api/videos/import-playlist` — import playlist (fetches via noembed.com)
  - `DELETE /api/videos/{id}` — delete

---

## Panel 3: Practice Problems

### Drawer Contents
- **Header**: "Practice Problems" + question count badge + "New Question" button
- **Two tabs**:
  - **Upload tab**: Same drag-and-drop zone as file panels (PDF/doc upload for existing problem sets); files stored under `static/uploads/practice/`
  - **Create tab**: Inline form:
    - Question text (textarea)
    - Type selector: `Multiple Choice` or `Free Text`
    - For MCQ: up to 4 answer options with a radio to mark correct answer
    - Submit adds to question bank
- **Question list**: Each question shows truncated text, type tag (`MCQ` or `Free Text`), delete (×) on hover; click to expand full question + answer

### Backend
- New `questions` table: `id`, `question_text`, `question_type` (mcq/free_text), `options` (JSON), `correct_answer`, `created_at`, `user_id`
- New `/api/questions` router:
  - `GET /api/questions` — list all
  - `POST /api/questions` — create question
  - `DELETE /api/questions/{id}` — delete
- Uploaded problem set files handled by the same `/api/files` router with `section=practice`

---

## Panel 4: Study Group

### Drawer Contents
- **Header**: "Study Group" + online member count badge
- **Members section** (top half):
  - Each member: amber initial circle + name + status dot (green = online, dim = offline)
  - Stats per member: hours studied this week, current streak
  - "Invite" button → inline form with name input to add a member
- **Shared feed** (bottom half):
  - Scrollable message feed: author initial, message text, timestamp per entry
  - Text input + "Post" button at the bottom
  - Messages persist in SQLite

### Backend
- New `members` table: `id`, `name`, `created_at`, `user_id`
- New `group_messages` table: `id`, `member_id`, `content`, `created_at`
- New `/api/group` router:
  - `GET /api/group/members` — list members
  - `POST /api/group/members` — add member
  - `GET /api/group/messages` — list messages
  - `POST /api/group/messages` — post message
  - `DELETE /api/group/messages/{id}` — delete message

---

## Shared UI Patterns

### Drawer Animation
- CSS `transform: translateX(100%)` → `translateX(0)` on open, with `transition: 0.25s ease`
- Main grid uses `transition: width 0.25s ease` to compress smoothly

### File Upload
- HTML `<input type="file">` hidden, triggered by click on drop zone
- Drag events (`dragover`, `drop`) handled in JS
- `FormData` + `fetch` for upload

### noembed.com Usage
- Fetch `https://noembed.com/embed?url={youtube_url}` to get title and thumbnail
- No API key required, works for both individual videos and playlist pages

### Existing Patterns Preserved
- All new inputs use `.note-input` class
- All new buttons use `.btn` / `.btn.primary` classes
- No new CSS frameworks introduced
- Single `index.html` file — all new styles and JS added inline

---

## Database Changes
All new tables auto-created via `Base.metadata.create_all`. No migrations needed.

New tables: `files`, `videos`, `questions`, `members`, `group_messages`

New routers: `app/routers/files.py`, `app/routers/videos.py`, `app/routers/questions.py`, `app/routers/group.py`

---

## Out of Scope
- Real-time features (WebSockets for group chat) — messages refresh on panel open only
- Authentication / multi-user — `user_id` defaults to 1 as per existing convention
- Video transcoding or local video storage — YouTube embeds only
- AI question generation
