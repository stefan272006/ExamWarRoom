# Frontend Roadmap

## Overview
Wire the existing static `index.html` to the FastAPI backend, and expand it with a fixed left sidebar, a persistent top bar, a push-drawer/split-pane system, and seven resource panels — all scoped to the currently selected course. No CSS frameworks. All styles and JS remain inline in `index.html`.

Phase 3 adds workspace flexibility: a collapsible sidebar, floating draggable/resizable windows for video and file preview, real AI flashcard generation via user-supplied Anthropic API key, and shareable study group invite links.

## Prerequisites
- Backend (Phase 1) must be complete and running
- All existing API endpoints returning correct responses

---

## Phase 2A — Existing Features (Wire to Backend)

### 1. API Helper
- [x] `api(path, opts)` fetch wrapper — handles Content-Type, JSON, error checking
- [x] `apiUpload(path, formData)` helper for multipart file uploads

### 2. Course Context
- [x] On page load: `GET /api/courses` → populate `#course-select` dropdown in top bar
- [x] If no courses exist: show empty state prompt — "No courses yet. Add one to get started." with an inline "+ Add Course" input
- [x] "+ Add Course" button in top bar (next to the dropdown): opens a small inline form (name input + confirm); submits `POST /api/courses`; on success the new course is appended to the dropdown and selected automatically
- [x] Store active course as `activeCourseId` in module-level state and `localStorage`
- [x] Restoring `activeCourseId` from `localStorage` on load: verify the course still exists in the fetched list before applying; fall back to first course if not found
- [x] Changing the dropdown re-fetches all course-scoped data (exams, stats, videos, files, questions, flashcards, progress)
- [x] All subsequent API calls append `?course_id={activeCourseId}` (or include it in the request body)

### 3. Exams
- [x] Dynamic load from `GET /api/exams`
- [x] Add exam form → `POST /api/exams`
- [x] Delete → `DELETE /api/exams/{id}`
- [x] Hero countdown from first exam date
- [x] Urgency tags: <10 days = `urgent`, <20 days = `soon`, else `planned`
- [x] Badge text: "N upcoming"

### 4. Notes
- [x] Load from `GET /api/notes`, render `#notes-list`
- [x] `POST /api/notes` on Enter
- [x] Delete → `DELETE /api/notes/{id}`

### 5. Focus Timer + Stats
- [x] Timer start/pause/reset client-side
- [x] **Timer persistence via localStorage:**
  - On start: save `{ startedAt: Date.now(), initialSeconds, modeKey, courseId }` to `localStorage['warroom_timer']`
  - On pause/reset: clear or update localStorage entry
  - On page load: read localStorage; if `startedAt` exists and matches active course, compute elapsed time and resume from correct position
- [x] On completion: `POST /api/sessions` with `{ duration_seconds, mode, subject, course_id }`
- [x] **Decimal accuracy:** `duration_seconds` must be the exact elapsed integer; the stats endpoint converts to hours server-side (`SUM / 3600.0`). Do not round to whole minutes.
- [x] Subject `<select>` populated from exams for active course
- [x] Load stats from `GET /api/sessions/stats?course_id={id}` → hours_studied (float, 1 decimal), session_count, day_streak
- [x] Stats display labelled "Total Hours — {CourseName}"
- [x] Re-fetch stats after each session completion

### 6. Study Progress
- [x] Load from `GET /api/progress`, render bars
- [x] Click to edit → `PUT /api/progress/{subject}`
- [x] Auto-created when exam added

### 7. Flashcards (client-side → backend-backed)
- [x] Remove hardcoded `cards` array
- [x] Load from `GET /api/flashcards?course_id={id}` on init and on course change
- [x] Render same flip-card UI, drive with fetched data
- [x] Flashcards panel in sidebar (see §13) handles CRUD; card widget in grid is read-only display

---

## Phase 2B — Layout

### 8. Top Bar
- [x] Persistent, full-width, fixed height (`52px`)
- [x] **Logo** (`War Room` box): make larger, cursor pointer, `onclick="goToDashboard()"` — returns to dashboard from any view
- [x] Live timer widget: `MM:SS · Mode` in amber monospace, always visible
- [x] **Course selector**: `<select id="course-select">` between logo and timer; styled to match `.note-input`; changing it triggers `onCourseChange()`

### 9. Left Sidebar
- [x] Fixed `220px` left panel
- [x] 7 resource buttons (adding Flashcards):
  - **Lecture Notes** — `✎` — `{n} files`
  - **Practice Problems** — `☰` — `{n} questions`
  - **Past Exams** — `∑` — `{n} files`
  - **Formula Sheets** — `▦` — `{n} files`
  - **Video Lectures** — `▶` — `{n} videos`
  - **Study Group** — `♣` — `{n} members`
  - **Flashcards** — `⊞` — `{n} cards`
- [x] Active state: amber left-border + amber text
- [x] Counts dynamic (fetched on load, updated after mutations)

### 10. Push-Drawer (default mode)
- [x] Fixed right drawer (`420px`) — push compresses main content
- [x] `transform: translateX` + `transition: width 0.25s ease`
- [x] Shared drawer shell; panel content injected dynamically
- [x] Opening new panel closes current one
- [x] Drawer header: title + × close button

### 11. Split-Pane Mode (new)
When the user activates "split view" (button in drawer header, or drag gesture):

- [x] Main content area switches from single-pane to **two-pane flex layout**:
  ```
  [sidebar] | [left-pane] [▐ drag-handle ▌] [right-pane]
  ```
- [x] **Drag handle**: a `4px` wide `div.split-handle` between panes; `cursor: col-resize`
  - `pointerdown` on handle → track `pointermove` on `document` → update left-pane flex-basis in `px`
  - `pointerup` → release; save split ratio to `localStorage['warroom_split']`
  - No external library; native pointer events only
- [x] Left pane: renders video player OR dashboard grid (user's choice)
- [x] Right pane: renders any open drawer panel (formula sheets, lecture notes, etc.)
- [x] "Split" button appears in drawer header next to ×; clicking it enters split mode and moves the drawer panel content into the right pane
- [x] "Exit split" button collapses right pane and restores single-pane layout
- [x] Minimum pane width: `280px` (enforced in drag handler)
- [x] Split ratio persists in `localStorage`; restored on next page load if split mode was active

---

## Phase 2C — Resource Panels

### 12. File Panels (Lecture Notes, Past Exams, Formula Sheets)
All three share the same drawer UI. `section` param maps to section name; `course_id` appended to all requests.

- [x] Upload zone: drag-and-drop + browse; `POST /api/files/upload` (FormData: `file`, `section`, `course_id`)
- [x] File list: filename, type tag, date, delete button → `DELETE /api/files/{id}`
- [x] Inline preview inside drawer: PDF → `<iframe>`, image → `<img>`, other → download link
- [x] "← Back" returns to file list
- [x] File count in sidebar subtext updates after mutations

### 13. Video Lectures Panel & Multitasking Player
- [x] Single URL input → noembed fetch → `POST /api/videos` (`{ url, title, thumbnail_url, course_id }`)
- [x] Playlist input → `POST /api/videos/import-playlist` (`{ playlist_url, course_id }`)
- [x] Video list: thumbnail + title + play/delete
- [x] **Video timestamp persistence:**
  - On leaving video view: read `videoIframe.contentWindow.postMessage` or query `youtube-nocookie` API for current time; store `{ videoId, timestamp }` in `localStorage['warroom_video_state']`
  - Fallback (cross-origin restriction): store `startedAt` + elapsed wall-clock time to approximate position
  - On returning to video: append `?start={seconds}` to embed URL
- [x] Clicking ▶ replaces dashboard with full-height player; drawer + top bar stay visible
- [x] "← Dashboard" returns to grid; playing video highlighted in list
- [x] In split-pane mode: video player occupies left pane; any panel occupies right pane simultaneously

### 14. Practice Problems Panel
- [x] Tabs: Questions / Create / Upload
- [x] Create: MCQ (up to 4 options + correct radio) or Free Text
- [x] `POST /api/questions` with `{ text, question_type, options?, correct_index?, course_id }`
- [x] Question list: expand to show full text + options
- [x] Delete → `DELETE /api/questions/{id}`

### 15. Study Group Panel
- [x] Members: invite, online/offline toggle, stats
- [x] Message feed: post, delete
- [x] No course scoping for study group (group is shared across courses)

### 16. Flashcards Panel (new)
Course-scoped. Replaces the static client-side flashcard widget.

- [x] Drawer panel with two tabs: **Browse** and **Create**
- [x] **Browse tab:**
  - Load from `GET /api/flashcards?course_id={id}`
  - Cards displayed as list items: truncated front text + edit (✎) + delete (×) buttons
  - Clicking a card flips it inline (CSS transform, same style as existing flashcard widget)
  - "Study mode" button → opens full-screen flip-card flow through all course cards
- [x] **Create tab:**
  - Front (textarea, `.note-input`, label "Question / Term")
  - Back (textarea, `.note-input`, label "Answer / Definition")
  - Submit → `POST /api/flashcards` with `{ front, back, course_id }`
  - After submit: switch to Browse tab, reload list
- [x] **Edit:** clicking ✎ on a card pre-fills the Create form and switches to that tab; submit → `PUT /api/flashcards/{id}`
- [x] **Delete:** `DELETE /api/flashcards/{id}` → reload list
- [x] **"Generate from Notes" button** (placeholder):
  - Amber dashed-border button at top of Browse tab: `⚡ Generate from Notes`
  - `onclick`: show loading spinner for 1.5s, then inject 3 mock flashcard objects into the list with a "Generated" badge (does NOT call backend — placeholder for future LLM integration)
- [x] Flashcard count in sidebar subtext (`{n} cards`) updates after CRUD
- [x] Dashboard flashcard widget loads from `GET /api/flashcards?course_id={id}` instead of hardcoded array

---

---

## Phase 3 — Workspace Flexibility

### 17. Collapsible Sidebar
- [ ] Toggle button (`‹‹` / `›`) at top of sidebar — shrinks sidebar to **48px icon-only strip**
- [ ] Collapsed state hides `.sb-name` and `.sb-count`; icons remain visible and centered
- [ ] CSS transition `width 0.25s ease` on `#sidebar`; toggled via `.sidebar-collapsed` class on `#app-shell`
- [ ] `title` attributes on all `.sb-btn` elements serve as tooltips in collapsed state
- [ ] Collapsed state persisted to `localStorage['warroom_sidebar']`; restored on page load
- [ ] `toggleSidebar()` function handles toggle + localStorage save + button label swap

### 18. FloatWin — Floating Window Utility
A generic JS utility (`const FloatWin = { ... }`) used by all floating panels.

- [ ] `FloatWin.create(id, label, bodyHtml, opts)` — creates a `position:fixed` floating window appended to `<body>`
  - `opts`: `{ x, y, w, h, minW, minH, extraTitleHtml }`
  - Title bar: `extraTitleHtml` (optional prefix, e.g. download button) + label + × close button
  - Body: `position:relative`, `overflow:hidden` — iframes fill it absolutely
  - Resize handle: bottom-right 16×16px triangle (`cursor: se-resize`)
- [ ] **Drag**: pointer events on titlebar; skips clicks on `button`, `a`, `input` children; constrained to viewport
- [ ] **Resize**: pointer events on bottom-right handle; enforces `minW`/`minH`
- [ ] **Z-order**: `pointerdown` on any float window brings it to front (`z-index` counter `_floatZ`)
- [ ] `FloatWin.close(id)` — removes window from DOM
- [ ] `FloatWin.isOpen(id)` — returns boolean
- [ ] Multiple float windows can be open simultaneously and independently moved

### 19. Floating Video Player
Replaces the full-screen takeover approach. Dashboard stays visible while video plays.

- [ ] `playVideo(video)` opens a `FloatWin` (`id='float-video'`) instead of hiding the dashboard
  - Default position: `x:240, y:80`, size `640×400`, min `320×220`
  - YouTube embed URL with `autoplay=1` in `float-win-body` as full-size `<iframe>`
  - Closing the float window saves video timestamp via `saveVideoTimestamp(videoId)`
  - Opening a new video while one is playing closes the old one first, saving its timestamp
- [ ] `saveVideoTimestamp(videoId)` — extracted helper that accumulates wall-clock elapsed time into `localStorage['warroom_video_state']`
- [ ] `backToDashboard()` — closes float-video window, clears `currentVideoId`, saves timestamp
- [ ] Playing video highlighted in video list (existing `playing` class logic preserved)

### 20. Floating File Preview + Download Button
File preview no longer replaces the drawer file list; opens as its own floating window.

- [ ] `showFilePreview(file, section)` opens a `FloatWin` (`id='float-file'`) instead of injecting into the drawer
  - Default position: `x:280, y:110`, size `520×520`, min `280×220`
  - PDF → `<iframe>` filling the body; image → centered `<img>`; other → download link fallback
  - **Download button** (`↓`) always visible in titlebar via `extraTitleHtml` option — `<a download>` pointing to `/api/files/{id}/content`
- [ ] Video and file preview windows can be open simultaneously and independently arranged

### 21. Settings Modal + Real AI Flashcard Generation
Replaces the mock `generateFromNotes()` with a real Claude API call.

- [ ] **Settings modal** (`#settings-modal`): full-screen backdrop, centered panel
  - Opened via `⚙` button in `.topbar-right`
  - Single field: Anthropic API key (`type="password"`, placeholder `sk-ant-api03-…`)
  - Saved to `localStorage['warroom_ai_key']`; cleared if field left blank
  - Backdrop click closes the modal
- [ ] `openSettings()` / `closeSettings()` / `saveApiKey()` functions
- [ ] `generateFromNotes()` — real implementation:
  - If no API key in localStorage → calls `openSettings()` instead
  - `POST /api/ai/generate-flashcards` with `{ course_id, api_key, source: 'both' }`
  - On success: calls `renderFlashcardList(existing, generated)` with real cards + "Generated" badge
  - Error handling: 401 → prompt to fix key in settings; 422 → "no content found" message
  - Button shows `⟳ Generating…` during request; restored on completion

### 22. Study Group Invite Links
Replaces the name-only invite form with a shareable single-use link system.

- [ ] **"⛓ Link" button** in Study Group panel header (beside existing "+ Invite" button)
- [ ] `generateInviteLink()` — calls `POST /api/group/invite` → receives `{ token, url }`
  - Opens a `FloatWin` (`id='float-invite'`) with the invite URL displayed in a readonly input
  - "Copy" button uses `navigator.clipboard.writeText()`; shows "Copied!" feedback for 1.5s
  - URL auto-selected for easy manual copy
- [ ] **Join flow**: on page load, `checkJoinToken()` checks for `?join=TOKEN` in URL
  - If token present: `history.replaceState` removes it from URL; `showJoinModal(token)` opens
  - Modal shows name input; on submit: `POST /api/group/join` with `{ token, name }`
  - Invalid/used token → alert message
- [ ] `checkJoinToken()` called as first line of `init()`

---

## UI Patterns

### Course-Scoped Reload
```js
async function onCourseChange() {
  activeCourseId = parseInt(document.getElementById('course-select').value);
  localStorage.setItem('warroom_course', activeCourseId);
  // Re-fetch all course-scoped data in parallel
  await Promise.all([
    loadExams(), loadNotes(), loadStats(), loadProgress(),
    loadSidebarCounts(), loadFlashcards()
  ]);
  // If a panel is open, re-render it with new course data
  if (currentPanel) renderPanel(currentPanel);
}
```

### Timer Persistence
```js
// On start:
localStorage.setItem('warroom_timer', JSON.stringify({
  startedAt: Date.now(),
  initialSeconds: timerInitialSeconds,
  modeIndex,
  courseId: activeCourseId
}));

// On page load:
const saved = JSON.parse(localStorage.getItem('warroom_timer') || 'null');
if (saved && saved.courseId === activeCourseId) {
  const elapsed = Math.floor((Date.now() - saved.startedAt) / 1000);
  timerSeconds = Math.max(0, saved.initialSeconds - elapsed);
  modeIndex = saved.modeIndex;
  // resume
}
```

### Split-Pane Drag
```js
let isDragging = false;
splitHandle.addEventListener('pointerdown', (e) => {
  isDragging = true;
  splitHandle.setPointerCapture(e.pointerId);
});
document.addEventListener('pointermove', (e) => {
  if (!isDragging) return;
  const shellLeft = appShell.getBoundingClientRect().left + sidebarWidth;
  const newWidth = Math.max(280, Math.min(e.clientX - shellLeft, totalWidth - 280));
  leftPane.style.flexBasis = newWidth + 'px';
});
document.addEventListener('pointerup', () => {
  if (!isDragging) return;
  isDragging = false;
  localStorage.setItem('warroom_split', leftPane.style.flexBasis);
});
```

### Inline Forms, Delete Buttons, Subject Dropdown, Drawer Tabs
(unchanged from previous spec)

### Push-Drawer Width Rules
| State | Main content width |
|---|---|
| Drawer closed | `calc(100vw - 220px)` |
| Drawer open (push mode) | `calc(100vw - 220px - 420px)` |
| Split-pane mode | Left pane + handle + right pane fill `calc(100vw - 220px)` |

---

## Verification

**Course scoping:**
- [x] Select "MATH 2030" → all panels show only MATH 2030 data
- [x] Add video under EECS 2001 → switch to MATH 2030 → video not visible
- [x] Stats show hours for active course only

**Timer persistence:**
- [x] Start timer → refresh page → timer resumes at correct position
- [x] Close tab mid-session → reopen → timer shows correct elapsed time
- [x] 30-minute session logged as `0.5` in hours_studied stat

**Split-pane:**
- [x] Click "Split" in drawer header → right pane shows panel content, left shows dashboard
- [x] Drag handle resizes panes smoothly, minimum 280px enforced
- [x] Split ratio persists across refresh
- [x] Video player in left pane + Formula Sheets in right pane simultaneously visible

**Logo navigation:**
- [x] Click "War Room" logo from video player → returns to dashboard
- [x] Returning to same video resumes at approximately correct timestamp

**Flashcards:**
- [x] Create card → appears in Browse tab → appears in dashboard widget
- [x] Edit card → form pre-filled → save updates in place
- [x] Delete card → removed from list and dashboard widget
- [x] "Generate from Notes" → spinner → 3 mock cards appear with "Generated" badge
- [x] Switching courses updates flashcard widget to new course cards

**Existing features (regression):**
- [x] All Phase 2A features still work with course scoping
- [x] Page loads with existing dark design intact
- [x] Flashcards/Study Group unaffected by course switch

**Sidebar collapse (Phase 3):**
- [ ] Click `‹‹` → sidebar collapses to 48px icon strip; icons + tooltips visible
- [ ] Click `›` → sidebar expands back to 220px
- [ ] Collapsed state persists across page refresh

**Floating windows (Phase 3):**
- [ ] Click ▶ on a video → dashboard stays visible; floating video window appears
- [ ] Drag video window by titlebar; resize from bottom-right corner handle
- [ ] Click file in drawer → floating file preview appears with ↓ download button in titlebar
- [ ] Video and file preview windows open simultaneously and independently draggable
- [ ] Closing float window via × saves video timestamp

**AI flashcards (Phase 3):**
- [ ] Click ⚙ → settings modal opens; API key saved to localStorage
- [ ] Click ⚡ Generate without key → settings modal opens automatically
- [ ] With key + uploaded PDF/notes → real flashcards generated and shown with "Generated" badge
- [ ] Invalid key → error prompt to update settings

**Invite links (Phase 3):**
- [ ] Study Group → ⛓ Link → floating window with copyable URL
- [ ] Opening invite URL → join modal appears; enter name → member added to group
- [ ] Re-opening same URL → "already used" error
