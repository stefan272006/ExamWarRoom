# Frontend Roadmap

## Overview
Wire the existing static `index.html` to the FastAPI backend, and expand it with a left sidebar, right-side resource drawers, and five new functional panels. No CSS frameworks introduced. All styles and JS remain inline in `index.html`.

## Prerequisites
- Backend (Phase 1) must be complete and running
- All existing API endpoints returning correct responses

---

## Phase 2A — Existing Features (Wire to Backend)

### 1. API Helper
- [ ] Add `api(path, opts)` fetch wrapper at top of `<script>` block
- Handles Content-Type header, JSON serialization, error checking

### 2. Exams
- [ ] Replace hardcoded exam list with dynamic loading from `GET /api/exams`
- [ ] Add inline "Add Exam" form inside the exam card (hidden by default, toggled by button)
  - Fields: name (text), subject (text), exam_date (datetime-local)
  - Inputs use `.note-input` class, submit button uses `.btn.primary`
  - On submit: `POST /api/exams`, re-render list, hide form
- [ ] Add delete button (styled "x") on each exam item → `DELETE /api/exams/{id}`
- [ ] Hero countdown reads first exam's `exam_date` from fetched data
- [ ] Urgency tags computed client-side: <10 days = `urgent`, <20 days = `soon`, else `planned`
- [ ] Card badge text updates dynamically (e.g. "3 upcoming")

### 3. Notes
- [ ] Load notes from `GET /api/notes` on page load, render into `#notes-list`
- [ ] Modify `handleNote()`: after creating DOM element, also `POST /api/notes`
- [ ] Store returned `id` on each note's DOM element
- [ ] Add delete button on each note → `DELETE /api/notes/{id}`

### 4. Focus Timer + Stats
- [ ] Timer start/pause/reset logic stays 100% client-side (no changes)
- [ ] On timer completion (timerSeconds reaches 0): `POST /api/sessions` with `{duration_seconds, mode, subject}`
- [ ] Add subject `<select>` dropdown to timer card, populated from exams' subjects
- [ ] Load stats from `GET /api/sessions/stats` on page load
- [ ] Replace animated dummy values with real data: hours_studied, session_count, day_streak
- [ ] `#stat-cards` stays client-side (flashcards not persisted)
- [ ] Re-fetch stats after each session is logged

### 5. Study Progress
- [ ] Load progress from `GET /api/progress` on page load, render bars dynamically
- [ ] Make progress bars editable: click to show a number input, on change `PUT /api/progress/{subject}`
- [ ] New subjects auto-created at 0% when exams are added (handled by backend)

### 6. Flashcards
- No changes — stays client-side with the hardcoded `cards` array

---

## Phase 2B — Layout Redesign

### 7. Top Bar
- [ ] Add persistent timer widget on the right side of the top bar
  - Shows current timer state: `25:00 · Pomodoro` in amber monospace
  - Always visible regardless of which panel is open
  - Updates live as the timer runs

### 8. Left Sidebar
- [ ] Add fixed left sidebar (~220px wide)
  - Background: `--surface` with 1px right border using `--amber-dim`
  - App logo/title at top
  - 6 resource buttons stacked vertically, each with: icon + name + count subtext
  - Active state: amber left-border accent + amber text
  - Hover state: `--amber-glow` background
- [ ] Main content area shifts right to fill remaining width (minus sidebar)

### 9. Right Drawer System
- [ ] Sliding right drawer (~420px wide), shared by all 6 resource panels
- [ ] Opens with CSS `transform: translateX(100%)` → `translateX(0)`, `transition: 0.25s ease`
- [ ] Main grid compresses to fit remaining width on open (`transition: width 0.25s ease`)
- [ ] Header with section title + close (×) button
- [ ] Opening a new panel closes the current one
- [ ] Closing restores full grid width

---

## Phase 2C — Resource Panels

### 10. File Panels (Lecture Notes, Past Exams, Formula Sheets)
All three share the same drawer UI:
- [ ] Header: section title + file count badge + "Upload" button (amber)
- [ ] Upload zone: drag-and-drop area with dashed amber border; "Drop files here or click to browse"; accepts PDF, images, common doc formats
  - Hidden `<input type="file">`, triggered by click or drag events
  - `FormData` + `fetch` for upload to `POST /api/files/upload?section=<name>`
- [ ] File list: filename, file type tag (`PDF`, `PNG`, etc.), upload date (dim monospace), delete (×) on hover → `DELETE /api/files/{filename}?section=<name>`
- [ ] Inline preview: clicking a file expands preview pane below list
  - PDFs: native `<iframe>` embed
  - Images: `<img>` inline
  - "Close Preview" link collapses it
- [ ] File count in sidebar subtext updates after upload/delete

### 11. Video Lectures Panel
- [ ] Header: "Video Lectures" + video count badge
- [ ] Single video input: text field for YouTube URL + "Add" button
  - On submit: fetch title/thumbnail via `https://noembed.com/embed?url={url}`, then `POST /api/videos`
- [ ] Playlist input: text field for YouTube playlist URL + "Import" button
  - On submit: `POST /api/videos/import-playlist`, re-render list
- [ ] Video list: thumbnail + title per entry, play (▶) and delete (×) on hover → `DELETE /api/videos/{id}`
- [ ] Clicking a video: embeds `<iframe>` YouTube player in the main content area (replaces dashboard grid)
  - Right drawer stays open with video list for easy switching
  - Top-bar timer remains visible
  - "Back to Dashboard" button returns to grid view

### 12. Practice Problems Panel
- [ ] Header: "Practice Problems" + question count badge + "New Question" button
- [ ] Two tabs inside drawer: **Upload** and **Create**
- [ ] Upload tab: same drag-and-drop zone as file panels; files go to `section=practice`
- [ ] Create tab: inline form
  - Question text (textarea, `.note-input`)
  - Type selector: `Multiple Choice` or `Free Text`
  - MCQ: up to 4 answer option inputs + radio to mark correct answer
  - Submit → `POST /api/questions`, re-render list
- [ ] Question list: truncated question text, type tag (`MCQ` or `Free Text`), delete (×) on hover → `DELETE /api/questions/{id}`
  - Click to expand: shows full question + answer

### 13. Study Group Panel
- [ ] Header: "Study Group" + online member count badge
- [ ] Members section (top half of drawer):
  - Each member: amber initial circle + name + status dot (green = online, dim = offline)
  - Online/offline is a manual toggle per member (click status dot to toggle → `PUT /api/group/members/{id}`)
  - Stats per member: hours studied this week, current streak
  - "Invite" button → inline form with name input → `POST /api/group/members`
- [ ] Shared feed (bottom half):
  - Scrollable message feed: author initial, message text, timestamp
  - Text input + "Post" button → `POST /api/group/messages`
  - Messages load on panel open from `GET /api/group/messages`
  - Delete (×) on hover → `DELETE /api/group/messages/{id}`

---

## UI Patterns

### Inline Forms
- Hidden `<div>` toggled by button in card/drawer header
- Same styling as existing quick-notes input (`.note-input` class)
- Submit with `.btn.primary`, cancel with `.btn`
- After submit: hide form, re-render list

### Delete Buttons
- Small "x" character, `color: var(--text-dim)`, no border
- On hover: `color: var(--red)`
- Positioned at end of list items

### Subject Dropdown
- `<select>` styled to match `.note-input`
- Populated dynamically from exams list
- First option: "No subject" (sends null)

### Drawer Tabs
- Tab buttons styled like `.btn` (monospace, small, uppercase)
- Active tab: amber bottom border + amber text
- Tab content panels toggled with `display: none` / `display: block`

---

## Verification
All tests done at `http://localhost:8000`:

**Existing features:**
- [ ] Page loads with existing dark design intact
- [ ] Add exam → appears in list → countdown updates → refresh → persists
- [ ] Delete exam → removed → refresh → stays removed
- [ ] Type note + Enter → appears → refresh → persists
- [ ] Delete note → removed → refresh → stays removed
- [ ] Complete focus timer → stats update → refresh → persists
- [ ] Edit progress percentage → refresh → persists
- [ ] Flashcards still work (click to reveal, prev/next)
- [ ] Empty state: no errors in console

**New layout:**
- [ ] Sidebar visible and fixed on scroll
- [ ] Clicking resource button opens correct drawer
- [ ] Grid compresses when drawer opens, restores when closed
- [ ] Timer widget always visible in top bar

**File panels:**
- [ ] Upload file → appears in list → refresh → persists
- [ ] Click file → preview opens inline
- [ ] Delete file → removed from list and filesystem

**Video lectures:**
- [ ] Paste YouTube URL → video added with title + thumbnail
- [ ] Import playlist URL → all videos appear
- [ ] Click video → player embeds in main area, drawer stays open
- [ ] "Back to Dashboard" → grid restored

**Practice problems:**
- [ ] Upload problem set PDF → appears in file list
- [ ] Create MCQ question → appears in question list → refresh → persists
- [ ] Expand question → shows full text + correct answer
- [ ] Delete question → removed

**Study group:**
- [ ] Add member → appears in list
- [ ] Toggle online/offline → dot changes color → persists on refresh
- [ ] Post message → appears in feed → refresh → persists
- [ ] Delete message → removed
