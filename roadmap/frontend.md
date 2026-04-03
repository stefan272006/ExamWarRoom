# Frontend Roadmap

## Overview
Wire the existing static `index.html` to the FastAPI backend. No CSS changes. All modifications are in the `<script>` block and minimal HTML additions for forms.

## Prerequisites
- Backend (Phase 1) must be complete and running
- All API endpoints returning correct responses

## Implementation Steps

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

## UI Patterns

### Inline Forms
- Hidden `<div>` toggled by a button in the card header
- Same styling as the existing quick-notes input (`.note-input` class)
- Submit with `.btn.primary`, cancel with `.btn`
- After submit: hide form, re-render the list

### Delete Buttons
- Small "x" character, `color: var(--text-dim)`, no border
- On hover: `color: var(--red)`
- Positioned at the end of list items

### Subject Dropdown
- `<select>` styled to match `.note-input` (dark background, monospace font, amber border on focus)
- Populated dynamically from the exams list
- First option: "No subject" (sends null)

## Verification
All tests done at `http://localhost:8000`:

- [ ] Page loads with existing dark design intact
- [ ] Add exam via form → appears in list → countdown updates → refresh → persists
- [ ] Delete exam → removed from list → refresh → stays removed
- [ ] Type note + Enter → appears in list → refresh → persists
- [ ] Delete note → removed → refresh → stays removed
- [ ] Complete a focus timer → stats update → refresh → persists
- [ ] Edit progress percentage → refresh → persists
- [ ] Flashcards still work (click to reveal, prev/next)
- [ ] Empty state: page loads correctly with no data (no errors in console)
