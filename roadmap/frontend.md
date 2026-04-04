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
Progress is confidence-driven — users tag each subject, and a computed score reflects both confidence + time studied.

**Loading and rendering:**
- [x] Load from `GET /api/progress?course_id={id}` on init and course change; each item includes `{ id, subject, confidence, progress_pct, updated_at }`
- [x] `renderProgress(items)` — builds one row per subject:
  - Confidence tag button: `<button class="confidence-tag c{n}" onclick="cycleConfidence(this)" data-subject="{subject}" data-confidence="{n}">{label}</button>`
  - Labels: `0` → `🔴 Struggling`, `1` → `🟡 Getting There`, `2` → `🟢 Confident`
  - Progress bar fill: `<div class="progress-fill c{n}" style="width:{progress_pct}%"></div>` — color matches confidence level (red / amber / green)
  - Delete button: `<button class="icon-btn" onclick="deleteProgress(this)" data-subject="{subject}">×</button>`
- [x] After rendering rows, call `renderProgressInsights(items)`:
  - If 2+ subjects exist: show "💪 Focus area: {lowest_pct subject}" and "⭐ Strength: {highest_pct subject}" in `#progress-insights` div below the list
  - Else: clear `#progress-insights`

**Confidence cycling (`cycleConfidence(btn)`):**
- [x] Read current `data-confidence` from button; compute `next = (current + 1) % 3`
- [x] Optimistic update: immediately update button class/text and bar color/class in DOM
- [x] `PUT /api/progress/{subject}` with `{ confidence: next, course_id }`
- [x] On success: apply returned `progress_pct` to bar width; update `data-confidence`
- [x] On error: roll back button and bar to previous values; show brief toast

**Subject delete (`deleteProgress(btn)`):**
- [x] Fade the row out (CSS opacity transition); `DELETE /api/progress/{subject}?course_id={id}`
- [x] On success: remove row from DOM; re-run `renderProgressInsights` on remaining rows
- [x] On error: fade row back in

**Manual subject add:**
- [x] `+ Subject` button in progress card header — `<button onclick="toggleSubjectForm()">+ Subject</button>`
- [x] Clicking it shows/hides an inline form: text input + "Add" button + `handleSubjectKey` on keydown (Enter submits, Escape hides)
- [x] `submitSubject()` — `POST /api/progress` with `{ subject, course_id }`; 409 → alert "Subject already exists"; on 201 → call `loadProgress()` to refresh the full list; hide form

**CSS additions:**
```css
.confidence-tag { font-family: var(--font-mono); font-size: 0.7rem; padding: 0.1rem 0.4rem;
  cursor: pointer; border: 1px solid; border-radius: 2px; background: none;
  transition: all 0.2s ease; white-space: nowrap; }
.confidence-tag.c0 { color: var(--red);   border-color: var(--red); }
.confidence-tag.c1 { color: var(--amber); border-color: var(--amber-dim); }
.confidence-tag.c2 { color: var(--green); border-color: var(--green); }
.progress-fill.c0 { background: var(--red); }
.progress-fill.c1 { background: var(--amber); }
.progress-fill.c2 { background: var(--green); }
.progress-insights { margin-top: 0.9rem; padding-top: 0.7rem; border-top: 1px solid var(--border);
  font-family: var(--font-mono); font-size: 0.6rem; color: var(--text-muted);
  display: flex; flex-direction: column; gap: 0.25rem; }
```

**HTML additions in progress card:**
```html
<!-- In card header, beside title -->
<button onclick="toggleSubjectForm()">+ Subject</button>

<!-- Inline form (hidden by default) -->
<div id="subject-form" style="display:none">
  <input id="subject-input" class="note-input" placeholder="Subject name"
         onkeydown="handleSubjectKey(event)">
  <button class="btn" onclick="submitSubject()">Add</button>
</div>

<!-- Below #progress-list -->
<div id="progress-insights"></div>
```

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
- [x] Toggle button (`‹‹` / `›`) at top of sidebar — shrinks sidebar to **48px icon-only strip**
- [x] Collapsed state hides `.sb-name` and `.sb-count`; icons remain visible and centered
- [x] CSS transition `width 0.25s ease` on `#sidebar`; toggled via `.sidebar-collapsed` class on `#app-shell`
- [x] `title` attributes on all `.sb-btn` elements serve as tooltips in collapsed state
- [x] Collapsed state persisted to `localStorage['warroom_sidebar']`; restored on page load
- [x] `toggleSidebar()` function handles toggle + localStorage save + button label swap

### 18. FloatWin — Floating Window Utility
A generic JS utility (`const FloatWin = { ... }`) used by all floating panels.

- [x] `FloatWin.create(id, label, bodyHtml, opts)` — creates a `position:fixed` floating window appended to `<body>`
  - `opts`: `{ x, y, w, h, minW, minH, extraTitleHtml }`
  - Title bar: `extraTitleHtml` (optional prefix, e.g. download button) + label + `—` minimize button + × close button
  - Body: `position:relative`, `overflow:hidden` — iframes fill it absolutely
  - Resize handle: bottom-right 16×16px triangle (`cursor: se-resize`)
- [x] **Drag — click-and-hold only (no ghost-drag)**:
  - Attach `pointerdown` listener on the titlebar element
  - Set a boolean `_isDragging = false` — only set to `true` inside the `pointerdown` handler when `event.buttons === 1` (primary mouse button held)
  - `pointermove` on `document` checks `_isDragging` before moving — if `false`, return immediately
  - `pointerup` and `pointercancel` on `document` reset `_isDragging = false`
  - `setPointerCapture` on titlebar in `pointerdown` to keep tracking outside the element
  - Must skip drag initiation when `pointerdown` target is a `button`, `a`, or `input` child
  - Constrain position so window never leaves viewport
  - **No hover-based movement** — window position must not change unless `event.buttons === 1` is confirmed
- [x] **Resize — click-and-hold only**:
  - Same `_isResizing` boolean pattern as drag; only set `true` in `pointerdown` handler with `event.buttons === 1`
  - `pointermove` checks `_isResizing` before resizing — if `false`, return immediately
  - `setPointerCapture` on resize handle in `pointerdown`
  - Enforces `minW`/`minH`
- [x] **Z-order**: `pointerdown` on any float window brings it to front (`z-index` counter `_floatZ`)
- [x] `FloatWin.close(id)` — removes window from DOM; clears it from the minimized items bar if present
- [x] `FloatWin.minimize(id)` — hides the window body + resize handle (sets `display:none`); collapses the window to just its titlebar height; adds a pill to the minimized items bar (see §22a)
- [x] `FloatWin.restore(id)` — removes the minimized bar pill; restores the window to its last known `{ x, y, w, h }` (stored in a `_floatState` map keyed by window id)
- [x] `FloatWin.isOpen(id)` — returns boolean (true even when minimized)
- [x] Multiple float windows can be open simultaneously and independently moved

### 18a. Minimized Items Bar
A fixed taskbar at the bottom of the screen that shows collapsed floating windows.

- [x] `<div id="minimized-bar">` — `position:fixed; bottom:0; left:0; right:0; height:36px; display:flex; align-items:center; gap:8px; padding:0 12px; background:#111; border-top:1px solid #333; z-index:9999`
- [x] Hidden (no children) by default; becomes visible when at least one window is minimized
- [x] Each minimized window appears as a pill: `<button class="min-pill">🗖 {label}</button>` — amber text, matte background, `cursor:pointer`
- [x] Clicking a pill calls `FloatWin.restore(id)` — restores the window to its last position/size and removes the pill
- [x] The × on a pill calls `FloatWin.close(id)` — permanently closes the window and removes the pill
- [x] The `—` minimize button in each FloatWin titlebar must not be confused with the × close button — use distinct icons: `—` for minimize, `×` for close

### 19. Floating Video Player
Replaces the full-screen takeover approach. Dashboard stays visible while video plays.

- [x] `playVideo(video)` opens a `FloatWin` (`id='float-video'`) instead of hiding the dashboard
  - Default position: `x:240, y:80`, size `640×400`, min `320×220`
  - YouTube embed URL with `autoplay=1` in `float-win-body` as full-size `<iframe>`
  - Closing the float window saves video timestamp via `saveVideoTimestamp(videoId)`
  - Opening a new video while one is playing closes the old one first, saving its timestamp
- [x] `saveVideoTimestamp(videoId)` — extracted helper that accumulates wall-clock elapsed time into `localStorage['warroom_video_state']`
- [x] `backToDashboard()` — closes float-video window, clears `currentVideoId`, saves timestamp
- [x] Playing video highlighted in video list (existing `playing` class logic preserved)

### 20. Floating File Preview + Download Button
File preview no longer replaces the drawer file list; opens as its own floating window.

- [x] `showFilePreview(file, section)` opens a `FloatWin` (`id='float-file'`) instead of injecting into the drawer
  - Default position: `x:280, y:110`, size `520×520`, min `280×220`
  - PDF → `<iframe>` filling the body; image → centered `<img>`; other → download link fallback
  - **Download button** (`↓`) always visible in titlebar via `extraTitleHtml` option — `<a download>` pointing to `/api/files/{id}/content`
- [x] Video and file preview windows can be open simultaneously and independently arranged

### 21. Settings Modal + Real AI Flashcard Generation
Replaces the mock `generateFromNotes()` with a real API call supporting both Anthropic and Google Gemini.

- [x] **Settings modal** (`#settings-modal`): full-screen backdrop, centered panel
  - Opened via `⚙` button in `.topbar-right`
  - **Two key fields:**
    - Anthropic API key (`id="settings-api-key"`, `type="password"`, placeholder `sk-ant-api03-…`) — paid, stored in `localStorage['warroom_ai_key']`
    - Gemini API key (`id="settings-gemini-key"`, `type="password"`, placeholder `AIza…`) — free tier, stored in `localStorage['warroom_gemini_key']`; label includes hint "Free at aistudio.google.com"
  - `saveApiKey()` writes or clears both keys; cleared if field left blank
  - `openSettings()` also populates both fields from localStorage before showing the modal
  - Backdrop click closes the modal
- [x] `openSettings()` / `closeSettings()` / `saveApiKey()` functions
- [x] **File selector in Flashcards Browse tab** (above the ⚡ Generate button):
  - `<select id="flashcard-file-select">` — `<option value="">From notes & all files</option>` as default, then one `<option value="{id}">{filename}</option>` per uploaded file for the active course
  - Populated by `loadFlashcardFileOptions()` which calls `GET /api/files?course_id={id}` (no section filter) and fills the select
  - Call `loadFlashcardFileOptions()` on panel open and on course change
  - Styled to match `.note-input`; label: "Generate from:"
- [x] `generateFromNotes()` — real implementation with provider selection:
  - Read both keys: `const anthropicKey = localStorage['warroom_ai_key']`, `const geminiKey = localStorage['warroom_gemini_key']`
  - If neither key is set → call `openSettings()` and return
  - **Provider selection**: prefer Anthropic if `anthropicKey` is set; fall back to Gemini if only `geminiKey` is set
  - Read selected file: `const fileId = document.getElementById('flashcard-file-select').value`
  - Build request body:
    - `provider`: `"anthropic"` or `"gemini"` depending on selection
    - `api_key` / `gemini_api_key`: whichever key the selected provider uses
    - If `fileId` non-empty: include `file_id: parseInt(fileId)`; else include `source: 'both'`
  - Button shows `⟳ Generating (Anthropic)…` or `⟳ Generating (Gemini)…` and is disabled during request
  - On success: call `renderFlashcardList(existing, generated)` with real cards + "Generated" badge
  - **Error handling:**
    - 400 → log only (guard above prevents reaching this)
    - 401 → show inline error "Invalid API key — update in ⚙ Settings"; call `openSettings()`
    - 402 (Anthropic no credits) → if Gemini key exists, auto-retry with Gemini via `_retryWithGemini(body)` helper; else show inline error "Anthropic account has no credits — add a Gemini key in ⚙ Settings for free generation"
    - 422 → show inline error "No content found for this selection"
    - 429 (Gemini quota) → show inline error "Gemini quota exceeded — try again later"
    - 503 → show inline error "SDK not installed on server — run `pip install anthropic` or `pip install google-generativeai`"
    - Other → show inline error "Generation failed, try again"
  - `_retryWithGemini(originalBody)` — extracted helper; replaces `provider`/key fields with Gemini values; re-POSTs; avoids recursive `generateFromNotes()` call; handles 429 and other errors inline without further fallback

### 22. Study Group Invite Links
Replaces the name-only invite form with a shareable single-use link system.

- [x] **"⛓ Link" button** in Study Group panel header (beside existing "+ Invite" button)
- [x] `generateInviteLink()` — calls `POST /api/group/invite` → receives `{ token, url }`
  - Opens a `FloatWin` (`id='float-invite'`) with the invite URL displayed in a readonly input
  - "Copy" button uses `navigator.clipboard.writeText()`; shows "Copied!" feedback for 1.5s
  - URL auto-selected for easy manual copy
- [x] **Join flow**: on page load, `checkJoinToken()` checks for `?join=TOKEN` in URL
  - If token present: `history.replaceState` removes it from URL; `showJoinModal(token)` opens
  - Modal shows name input; on submit: `POST /api/group/join` with `{ token, name }`
  - Invalid/used token → alert message
- [x] `checkJoinToken()` called as first line of `init()`

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
- [x] Click `‹‹` → sidebar collapses to 48px icon strip; icons + tooltips visible
- [x] Click `›` → sidebar expands back to 220px
- [x] Collapsed state persists across page refresh

**Floating windows (Phase 3):**
- [x] Click ▶ on a video → dashboard stays visible; floating video window appears
- [x] Drag video window by titlebar; resize from bottom-right corner handle
- [x] **Hovering over a window does NOT move or resize it** — movement only occurs while primary mouse button is held (ghost-drag bug fixed)
- [x] Click file in drawer → floating file preview appears with ↓ download button in titlebar
- [x] Video and file preview windows open simultaneously and independently draggable
- [x] Closing float window via × saves video timestamp

**Window minimization (Phase 3):**
- [x] Click `—` in a float window header → window body collapses; a pill appears in the minimized bar at the bottom of the screen
- [x] Minimized bar is invisible when no windows are minimized
- [x] Clicking the pill in the minimized bar → window re-opens at its last known position and size
- [x] Clicking × on the minimized bar pill → window is permanently closed and pill removed
- [x] Multiple windows can be minimized simultaneously; each has its own pill

**Study Progress — confidence tags (Phase 4):**
- [x] Add exam → subject auto-appears in progress list at 🔴 Struggling (confidence=0, pct=10)
- [x] Click tag → cycles 🔴→🟡→🟢→🔴; bar color and width update immediately (optimistic)
- [x] After server confirms: bar width reflects `progress_pct` from response (includes activity bonus)
- [x] Log a 2h focus session for a subject → revisit progress → bar nudges up even without changing tag
- [x] Click × delete button → row fades out and disappears; re-renders insights for remaining subjects
- [x] Click `+ Subject` → inline form appears; type name + Enter → subject added at 🔴 Struggling
- [x] Duplicate subject name → alert "Subject already exists"
- [x] With 2+ subjects: "💪 Focus area:" shows lowest-pct subject; "⭐ Strength:" shows highest-pct subject

**AI flashcards (Phase 3 + Phase 4):**
- [x] Click ⚙ → settings modal opens with both Anthropic and Gemini key fields
- [x] Click ⚡ Generate without any key → settings modal opens automatically
- [x] "Generate from:" dropdown lists all uploaded files for the active course
- [x] Select a specific file → Generate → real flashcards extracted from that file only
- [x] Select "From notes & all files" → Generate → content pulled from notes + all uploaded files
- [x] Anthropic key set, valid → button shows "⟳ Generating (Anthropic)…" → real cards appear
- [x] Invalid Anthropic key → settings modal auto-opens; inline error shown
- [x] Anthropic key has no credits (402) + Gemini key is set → auto-retries with Gemini; cards appear
- [x] Anthropic key has no credits (402) + no Gemini key → inline error prompting user to add Gemini key
- [x] Only Gemini key set → button shows "⟳ Generating (Gemini)…" → real cards appear
- [x] Gemini quota exceeded (429) → inline "quota exceeded" error (not a generic 500)
- [x] No content for selection → "No content found" inline error
- [x] SDK not installed on server → "run pip install …" inline error (not a generic 500)

**Invite links (Phase 3):**
- [x] Study Group → ⛓ Link → floating window with copyable URL
- [x] Opening invite URL → join modal appears; enter name → member added to group
- [x] Re-opening same URL → "already used" error

---

## Phase 5 — UI Redesign (Human-first Aesthetic)

### 28. Design Token Overhaul
- [x] Warm dark neutrals: `--bg` #1a1a1a, surfaces #212121 / #2a2a2a
- [x] New `--sage` / `--sage-dim` / `--sage-glow` tokens for break-mode accent
- [x] `--radius: 10px`, `--radius-sm: 6px`, `--shadow-card`, `--shadow-float` tokens added
- [x] Base font size bumped from 15px → 16px
- [x] Inter added as preferred body font: `'Inter', 'Libre Franklin', sans-serif`
- [x] Topbar backdrop color updated to match new `--bg`

### 29. Typography Cleanup
- [x] `.card-title`: switched to body font, removed uppercase/letter-spacing — cleaner, more readable
- [x] `.stat-label`: switched to body font, removed uppercase/letter-spacing
- [x] `.hero h1`: 2.8rem → 2.4rem; `.hero-sub`: 0.9rem → 1rem; `.hero-label` letter-spacing reduced
- [x] Mono font reserved for: time displays, timestamps, card badges, code values

### 30. Cards, Inputs & Sidebar Restyle
- [x] Cards: `border-radius: var(--radius)`, `box-shadow: var(--shadow-card)` — softer, elevated feel
- [x] Modals: `border-radius: var(--radius)`, `box-shadow: var(--shadow-float)`
- [x] Buttons (`.btn`) and inputs (`.note-input`): `border-radius: var(--radius-sm)`
- [x] Sidebar (`#sidebar`): `background: var(--bg)` — Notion-style: sidebar darker than content
- [x] Sidebar buttons: `border-left: 2px` (subtler), rounded right edge, neutral hover (not amber-washed)
- [x] Logo: body font, no border box, no uppercase — workspace-name style

### 31. Pomodoro Timer Redesign
- [x] Circular SVG progress ring (`r=52`, circumference ≈ 326.56px) centered around time display
- [x] Pill tab row (4 tabs: Pomodoro / Short Break / Long Break / Deep Focus) replaces "Mode" cycle button
- [x] Break modes (Short/Long Break) use `--sage` accent on ring + active tab; focus modes use `--amber`
- [x] Mode accent driven by `data-mode="focus|break"` attribute on `.timer-card` via CSS custom props
- [x] `setTimerMode(index)` replaces `switchTimerMode()` (shim preserved for safety)
- [x] `updateTimerTabUI(index)` helper updates tab active state + card mode attr without resetting timer
- [x] `displayTimer()` animates `stroke-dashoffset` proportional to remaining time each tick

### 32. Toast Notification System
- [x] `showToast(msg, opts)` — bottom-right sliding toast, auto-dismisses (default 4s), manually closable
- [x] Variant types: `info` (amber), `success` (green), `error` (red), `break` (sage) — left-border color coding
- [x] Replaces all 8 `alert()` call sites throughout the app — no more blocking browser dialogs
- [x] Timer completion triggers toast (6s duration) describing session or break completion
- [x] `playCompletionChime(isBreak)` — AudioContext sine-wave chime (3 notes focus, 2 notes break); silent fallback if blocked

**Verification:**
- [x] Background is `#1a1a1a`, cards have visible rounded corners and soft shadows
- [x] Sidebar is visually darker than main content area
- [x] Timer card shows 4 pill tabs; "Mode" button is absent
- [x] Switching to Short/Long Break → ring and active tab turn sage-green
- [x] Switching to Pomodoro/Deep Focus → ring and active tab turn amber
- [x] Ring drains in real time as timer ticks; resumes at correct fraction after page refresh
- [x] Duplicate subject → error toast (no browser alert)
- [x] Timer completes → toast slides in from bottom-right + soft chime plays

---

## Phase 6 — Complete UI Overhaul (Notion/Obsidian, No Amber)

**Goal:** Replace the entire visual identity. The current design is a "war room" terminal — amber on black, all-caps mono labels everywhere, hard 1px borders, aggressive accents. Phase 6 replaces this completely with a calm, human, premium dark UI inspired by Obsidian and Notion. Amber is removed entirely. The new accent is soft indigo (`#7c6af7`). Every implementation detail below is final — no guessing required.

**The file being edited is `static/index.html` (all CSS and JS inline in one file). No new files. No backend changes.**

---

### 33. New Design Token System

**Replace the entire `:root` block** with the following. Remove the old `--amber`, `--amber-dim`, `--amber-glow`, `--sage`, `--sage-dim`, `--sage-glow` tokens. Add the new accent system.

```css
:root {
  /* Backgrounds */
  --bg:             #1e1e1e;
  --surface:        #252525;
  --surface-raised: #2d2d2d;

  /* Borders — ghost rgba, not solid */
  --border:         rgba(255, 255, 255, 0.08);
  --border-light:   rgba(255, 255, 255, 0.13);

  /* Text */
  --text:           #e2e2e2;
  --text-muted:     #888888;
  --text-dim:       #525252;

  /* Accent — soft indigo (replaces ALL amber usage) */
  --accent:         #7c6af7;
  --accent-dim:     #6355d4;
  --accent-glow:    rgba(124, 106, 247, 0.12);

  /* Semantic colors */
  --red:            #e06c75;
  --green:          #98c379;
  --blue:           #61afef;

  /* Focus/break timer accents */
  --timer-focus:    #7c6af7;   /* indigo — same as --accent */
  --timer-break:    #98c379;   /* green */
  --timer-focus-glow: rgba(124, 106, 247, 0.12);
  --timer-break-glow: rgba(152, 195, 121, 0.12);

  /* Typography */
  --font-display:   'DM Serif Text', Georgia, serif;
  --font-mono:      'JetBrains Mono', 'Courier New', monospace;
  --font-body:      'Inter', sans-serif;

  /* Shape */
  --radius:         12px;
  --radius-sm:      8px;
  --radius-xs:      4px;

  /* Elevation */
  --shadow-sm:      0 1px 3px rgba(0,0,0,0.35);
  --shadow-card:    0 4px 24px rgba(0,0,0,0.45), 0 1px 4px rgba(0,0,0,0.3);
  --shadow-float:   0 24px 80px rgba(0,0,0,0.55), 0 4px 16px rgba(0,0,0,0.35);

  /* Layout */
  --topbar-h:       56px;
  --sidebar-w:      240px;
  --sidebar-collapsed-w: 52px;
  --drawer-w:       420px;
}

html { font-size: 16px; }
```

---

### 34. Global Amber Purge

There are ~75 references to amber in the codebase. **Every single one must be replaced** with the equivalent new token. Do a global find-and-replace:

| Find | Replace with |
|------|-------------|
| `var(--amber)` | `var(--accent)` |
| `var(--amber-dim)` | `var(--accent-dim)` |
| `var(--amber-glow)` | `var(--accent-glow)` |
| `#e2a83e` | `#7c6af7` |
| `#b8892e` | `#6355d4` |
| `rgba(226, 168, 62` | `rgba(124, 106, 247` |
| `rgba(226,168,62` | `rgba(124, 106, 247` |

After this replacement, update the timer-specific CSS:
- `.timer-card[data-mode="focus"]` → `--timer-accent: var(--timer-focus); --timer-accent-glow: var(--timer-focus-glow);`
- `.timer-card[data-mode="break"]` → `--timer-accent: var(--timer-break); --timer-accent-glow: var(--timer-break-glow);`
- `.timer-ring-fg` stroke color → `var(--timer-accent, var(--accent))`
- `.timer-tab.active` → background `var(--timer-accent, var(--accent))`
- `.topbar-timer-widget` color → `var(--accent)`
- `.topbar-timer-widget.running` → border-color `var(--accent)`
- Toast `.toast-info` → `border-left-color: var(--accent)`

Also update the `onTimerComplete` toast call in JS: change `type: 'info'` toast variant color reference from amber to accent (this is handled by the CSS token change above, no JS edit needed).

---

### 35. Typography System Overhaul

**Rule:** Mono font is for DATA only (numbers, timestamps, code values, status badges). Everything else uses Inter.

**Remove `font-family: var(--font-mono)` and `text-transform: uppercase` and `letter-spacing` from all of the following CSS rules** (edit each rule, keep other properties):

| Selector | Remove | Keep |
|----------|--------|------|
| `.topbar-icon-btn` | `font-family: var(--font-mono)` | everything else |
| `.logo` | already fixed in Phase 5 | — |
| `.course-select` | `font-family: var(--font-mono)` | — |
| `.add-course-btn` | `font-family: var(--font-mono)` | — |
| `.no-course-label` | `font-family: var(--font-mono)`, `letter-spacing` | — |
| `.sidebar-toggle` | `font-family: var(--font-mono)` | — |
| `.drawer-title` (in drawer header) | `font-family: var(--font-mono)`, `text-transform: uppercase`, `letter-spacing` → change to `font-family: var(--font-body); font-size: 0.875rem; font-weight: 600; letter-spacing: normal;` | — |
| `.panel-badge` | `font-family: var(--font-mono)`, `letter-spacing`, `text-transform` | — |
| `.countdown-unit` | keep mono but remove `letter-spacing: 0.15em` → use `0.05em` | — |
| `.empty-state` | `font-family: var(--font-mono)`, `letter-spacing` | — |
| `.upload-status` | `font-family: var(--font-mono)` | — |
| `.drop-formats` | `font-family: var(--font-mono)`, `letter-spacing` | — |
| `.file-date` | `font-family: var(--font-mono)` → change to `var(--font-body)` | — |
| `.footer-text` | `font-family: var(--font-mono)`, `letter-spacing` | — |
| `.modal-label` | `font-family: var(--font-mono)`, `text-transform: uppercase`, `letter-spacing` | — |
| `.inline-form .note-input` | inherited — fix via `.note-input` below | — |
| `.btn` | `font-family: var(--font-mono)`, `text-transform: uppercase`, `letter-spacing: 0.12em` → replace with `font-family: var(--font-body); font-size: 0.82rem; font-weight: 500; letter-spacing: normal; text-transform: none;` | keep all other properties |
| `.note-input` | `font-family: var(--font-mono)` → `var(--font-body)` | — |

**Mono stays on (do NOT change):**
`.timer-time`, `.countdown-num`, `.stat-num`, `.exam-date`, `.note-time`, `.card-badge`, `.confidence-tag`, `.exam-tag`, `.progress-add-btn`, `.topbar-timer-widget`

---

### 36. Border System — Ghost Borders

Since `--border` and `--border-light` are now `rgba` values, existing `border: 1px solid var(--border)` rules will automatically render as ghost borders. No per-element changes needed here.

**However**, three places use hardcoded colors that must be updated manually:
- `body::before` noise overlay — reduce opacity from `0.03` to `0.02`
- `.topbar` background — change `rgba(14, 14, 14, 0.92)` → `rgba(30, 30, 30, 0.92)`
- `.add-course-form` background — change `var(--surface)` → `var(--surface)` (no change, already correct)

---

### 37. Topbar

```css
.topbar {
  height: var(--topbar-h);  /* now 56px */
  background: rgba(30, 30, 30, 0.94);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(24px);
}

.logo {
  font-family: var(--font-body);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text);        /* neutral white, not accent */
  padding: 0.3rem 0;         /* remove box, no border, no padding box */
  letter-spacing: -0.01em;
}
.logo:hover { color: var(--accent); background: none; }

.topbar-icon-btn {
  font-family: var(--font-body);
  font-size: 0.8rem;
  background: var(--surface-raised);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  width: 32px;
  height: 32px;
}
.topbar-icon-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-glow); }

.course-select {
  font-family: var(--font-body);
  font-size: 0.82rem;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--surface-raised);
  color: var(--text);
}
.course-select:focus { border-color: var(--accent); }

.topbar-timer-widget {
  color: var(--accent);   /* was amber */
  font-family: var(--font-mono);
  font-size: 0.75rem;
}
.topbar-timer-widget.running { border-color: var(--accent); }
```

---

### 38. Sidebar — Document Navigator

```css
#sidebar {
  width: var(--sidebar-w);   /* now 240px */
  background: #1a1a1a;       /* slightly darker than --bg */
  border-right: 1px solid var(--border);
}

.sb-btn {
  font-family: var(--font-body);
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--text-muted);
  padding: 0.5rem 0.85rem;
  border: none;
  border-left: 2px solid transparent;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: transparent;
  gap: 0.65rem;
  transition: background 0.15s ease, color 0.15s ease;
}
.sb-btn:hover { background: rgba(255,255,255,0.05); color: var(--text); }
.sb-btn.active {
  border-left-color: var(--accent);
  color: var(--accent);
  background: var(--accent-glow);
  font-weight: 500;
}
.sb-btn.active .sb-count { color: var(--accent-dim); }

.sb-name { font-size: 0.875rem; font-weight: inherit; }
.sb-count { font-family: var(--font-body); font-size: 0.72rem; color: var(--text-dim); }

.sidebar-toggle {
  font-family: var(--font-body);
  font-size: 0.75rem;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-dim);
}
.sidebar-toggle:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-glow); }
```

---

### 39. Cards

```css
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);          /* 12px */
  padding: 1.75rem;
  box-shadow: var(--shadow-card);
  position: relative;
  overflow: hidden;
  animation: fadeUp 0.6s ease-out both;
}

/* Hover shimmer — update from amber-dim to accent */
.card::before {
  background: linear-gradient(90deg, transparent, var(--accent-dim), transparent);
}

.card-header { margin-bottom: 1.4rem; }

.card-title {
  font-family: var(--font-body);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: normal;
  text-transform: none;
}

.card-badge {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.18rem 0.5rem;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xs);
  color: var(--text-dim);
}
.card-badge.live { color: var(--accent); border-color: var(--accent-dim); }
```

---

### 40. Buttons

```css
.btn {
  font-family: var(--font-body);
  font-size: 0.82rem;
  font-weight: 500;
  letter-spacing: normal;
  text-transform: none;
  padding: 0.5rem 1.1rem;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-glow); }
.btn.primary { border-color: var(--accent); color: var(--accent); }
.btn.primary:hover { background: var(--accent); color: #fff; border-color: var(--accent); }
.btn.sm { padding: 0.3rem 0.7rem; font-size: 0.78rem; }
```

---

### 41. Inputs

```css
.note-input {
  font-family: var(--font-body);
  font-size: 0.875rem;
  font-weight: 400;
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 0.7rem 0.9rem;
  outline: none;
  transition: border-color 0.2s ease;
  resize: none;
  width: 100%;
}
.note-input::placeholder { color: var(--text-dim); }
.note-input:focus { border-color: var(--accent); }
```

---

### 42. Pomodoro Timer Card (premium, stays in 2-col grid)

```css
/* Mode accent system */
.timer-card[data-mode="focus"] {
  --timer-accent: var(--timer-focus);
  --timer-accent-glow: var(--timer-focus-glow);
}
.timer-card[data-mode="break"] {
  --timer-accent: var(--timer-break);
  --timer-accent-glow: var(--timer-break-glow);
}

/* Mode pill tabs */
.timer-mode-tabs {
  display: flex;
  gap: 0.25rem;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 1.4rem;
}
.timer-tab {
  font-family: var(--font-body);
  font-size: 0.72rem;
  font-weight: 500;
  padding: 0.28rem 0.8rem;
  border: 1px solid var(--border-light);
  border-radius: 100px;
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  transition: all 0.18s ease;
  white-space: nowrap;
}
.timer-tab:hover {
  border-color: var(--timer-accent, var(--accent));
  color: var(--timer-accent, var(--accent));
}
.timer-tab.active {
  background: var(--timer-accent, var(--accent));
  border-color: var(--timer-accent, var(--accent));
  color: #fff;
  font-weight: 600;
}

/* Ring */
.timer-ring-wrap {
  position: relative;
  width: 180px;
  height: 180px;
  margin: 0 auto 1.2rem;
}
.timer-ring-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.timer-ring-bg {
  fill: none;
  stroke: var(--border-light);
  stroke-width: 4;
}
.timer-ring-fg {
  fill: none;
  stroke: var(--timer-accent, var(--accent));
  stroke-width: 4;
  stroke-linecap: round;
  stroke-dasharray: 376.99;    /* 2π × 60  (r=60 for 180px ring) */
  stroke-dashoffset: 0;
  transition: stroke-dashoffset 1s linear, stroke 0.4s ease;
  filter: drop-shadow(0 0 6px var(--timer-accent, var(--accent)));
}
.timer-ring-inner {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.2rem;
}
.timer-time {
  font-family: var(--font-mono);
  font-size: 2.4rem;
  font-weight: 200;
  color: var(--text);
  letter-spacing: 0.02em;
  line-height: 1;
}

/* Controls */
.timer-controls { margin-top: 0.85rem; }
.timer-subject-select {
  font-family: var(--font-body);
  font-size: 0.8rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-raised);
  color: var(--text);
  padding: 0.4rem 0.7rem;
}
.timer-subject-select:focus { border-color: var(--accent); }
```

**JS update for ring:** The SVG ring has `r=52` but the new ring is `width/height: 180px`. Update the SVG in HTML:
```html
<svg class="timer-ring-svg" viewBox="0 0 140 140">
  <circle class="timer-ring-bg" cx="70" cy="70" r="60"/>
  <circle class="timer-ring-fg" id="timer-ring-fg" cx="70" cy="70" r="60"/>
</svg>
```
Update `displayTimer()` JS — change circumference constant from `326.56` to `376.99` (2π × 60).

---

### 43. Stats Section

```css
.stats-row { gap: 1.5rem; }
.stat-num {
  font-family: var(--font-mono);
  font-size: 1.8rem;
  font-weight: 300;
  color: var(--text);
}
.stat-label {
  font-family: var(--font-body);
  font-size: 0.75rem;
  font-weight: 400;
  color: var(--text-dim);
  margin-top: 0.3rem;
  text-transform: none;
  letter-spacing: normal;
}
```

---

### 44. Dashboard Hero

```css
.hero-label {
  font-family: var(--font-body);
  font-size: 0.72rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 0.5rem;
}
/* .hero h1 keeps DM Serif Text — display text is appropriate */
.hero h1 { font-size: 2.4rem; }
.hero h1 em { color: var(--accent); font-style: italic; }   /* accent replaces amber */
.hero-sub { font-size: 1rem; color: var(--text-muted); }

.countdown-num {
  color: var(--accent);   /* was amber */
}
```

---

### 45. Drawer + Panels

```css
.drawer-title {
  font-family: var(--font-body);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: normal;
  text-transform: none;
}

.panel-badge {
  font-family: var(--font-body);
  font-size: 0.72rem;
  font-weight: 400;
  color: var(--text-dim);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xs);
  padding: 0.1rem 0.4rem;
  text-transform: none;
  letter-spacing: normal;
}

.empty-state {
  font-family: var(--font-body);
  font-size: 0.82rem;
  color: var(--text-dim);
  letter-spacing: normal;
}
```

---

### 46. Modals

```css
.modal-panel {
  border-radius: var(--radius);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-float);
  background: var(--surface);
}
.modal-label {
  font-family: var(--font-body);
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: none;
  letter-spacing: normal;
  margin-bottom: 0.4rem;
}
```

---

### 47. Toast System — Accent Update

Update the existing toast CSS variants to use the new accent:
```css
.toast.toast-info    { border-left: 3px solid var(--accent); }
.toast.toast-success { border-left: 3px solid var(--green); }
.toast.toast-error   { border-left: 3px solid var(--red); }
.toast.toast-break   { border-left: 3px solid var(--timer-break); }
```

---

### 48. Progress + Confidence Tags

```css
.progress-fill        { background: var(--accent); }     /* was amber */
.progress-fill::after { background: var(--accent); }
.progress-fill.c1     { background: var(--accent); }     /* medium confidence = accent */
.progress-fill.c1::after { background: var(--accent); }

.confidence-tag.c1 { color: var(--accent); border-color: var(--accent-dim); }
.confidence-tag.c1:hover { background: var(--accent-glow); }

.progress-add-btn:hover { border-color: var(--accent-dim); color: var(--accent); }
```

---

### 49. Exam Tags + Misc Interactive

```css
.exam-tag.soon { color: var(--accent); border-color: var(--accent-dim); }  /* was amber */
.exam-item:hover { background: var(--accent-glow); }   /* was amber-glow */
.file-list-item:hover { background: var(--accent-glow); }
.video-list-item.playing { border: 1px solid var(--accent-dim); background: var(--accent-glow); }
.drop-zone { border: 1px dashed var(--accent-dim); }
.drop-zone.drag-over { background: var(--accent-glow); border-color: var(--accent); }
.drop-link { color: var(--accent); }
.play-btn { color: var(--accent); }
.split-handle:hover, .split-handle.dragging { background: var(--accent-dim); }
```

---

### 50. Flashcard Widget

```css
.flashcard:hover { border-color: var(--accent-dim); }
.flashcard-a { color: var(--accent); }   /* was amber */
```

---

### Verification Checklist

- [x] No amber/`#e2a83e` anywhere in the file — grep confirms 0 matches
- [x] Background is `#1e1e1e`, surface `#252525` — distinctly different, visible depth
- [x] Borders are ghost rgba — no hard visible grid lines
- [x] Sidebar active state: indigo left accent + indigo text + indigo glow
- [x] All buttons use Inter, no uppercase, no letter-spacing
- [x] All inputs use Inter body font
- [x] Drawer titles, modal labels, empty states use Inter — no mono
- [x] Timer ring is 180px, `r=60`, circumference `376.99`
- [x] Timer focus mode: indigo ring + indigo active tab
- [x] Timer break mode: green ring + green active tab
- [x] Ring has a subtle `drop-shadow` glow matching the current accent
- [x] Countdown numbers are accent color (indigo)
- [x] Hero `em` text is accent color (indigo)
- [x] Confidence `c1` (medium) tags/bars are indigo (not amber)
- [x] Toasts: `info` variant has indigo left border
- [x] No regressions: sidebar panels, timer persistence, flashcards, study group all function
