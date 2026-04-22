# Lute Progress Dashboard Plan

## Requirements Summary

Build a new progress dashboard for Lute with:
1. database migrations for `reading_sessions`, `goals`, and `milestones`
2. Flask JSON APIs at `/api/stats/overview`, `/api/stats/books`, `/api/stats/vocabulary`, and `/api/stats/streak`
3. a new `/progress` page using Chart.js for vocabulary distribution, book completion bars, reading heatmap, and streak counter
4. integration with existing Lute navigation, templates, and SQLite-backed reading/term data

## Current Codebase Facts

- Lute already tracks **books**, **texts/pages**, and **book reading status** in `Book` and `Text` (`lute/models/book.py:41-56`, `lute/models/book.py:172-180`).
- Lute already records a per-page historical read event in `wordsread` via `WordsRead` (`lute/models/book.py:285-308`), and page reads are appended when a page is marked read in `lute/read/service.py:83-94`.
- Lute already captures page-open timestamps via `Text.start_date` when reading starts (`lute/read/service.py:155-168`).
- Lute already has a `stats` blueprint with HTML and JSON routes (`lute/stats/routes.py:9-23`), currently backed by simple SQL aggregations over `wordsread` (`lute/stats/service.py:9-96`).
- Lute already ships Chart.js and renders a stats page client-side in `lute/templates/stats/index.html:9-155`.
- The top navigation currently exposes `Statistics` from the About menu in `lute/templates/base.html:126-130`.
- App registration already includes the stats blueprint in `lute/app_factory.py:65` and `lute/app_factory.py:351`.
- Existing vocabulary data is stored in `words`, including status, created date, and status-changed date (`lute/models/term.py:91-107`, `lute/db/schema/baseline.sql:119-130`), with triggers maintaining `WoStatusChanged` and updating `WoCreated` when a term first leaves unknown (`lute/db/schema/baseline.sql:292-310`).
- Existing book-level summary stats are cached in `bookstats` (`lute/models/book.py:399-407`, `lute/db/schema/baseline.sql:167-174`) and should remain separate from the new progress dashboard because they serve the books listing.

## Architecture Decision Summary

### Decision 1: Add new progress tables, but keep existing `wordsread` as the source-compatible legacy feed
Use new normalized progress tables for dashboard features while preserving `wordsread` for backward compatibility and historical backfill.

Why:
- `wordsread` only stores one row per read action with language/text/date/word_count (`lute/models/book.py:290-302`), which is enough for current charts but not enough for explicit goals/milestones or richer session metadata.
- `mark_page_read` already writes stable read events (`lute/read/service.py:83-94`), so migration can backfill from existing data instead of forcing users to lose history.

### Decision 2: Derive streaks, heatmap, and most vocabulary analytics from persisted facts rather than storing redundant counters
Do **not** create a dedicated streak table. Compute streaks from daily activity in `reading_sessions`/`wordsread`, and compute vocabulary progress from `words` timestamps/statuses.

Why:
- Existing term timestamps already encode “when a word became learned/non-unknown” (`lute/db/schema/baseline.sql:128-130`, `lute/db/schema/baseline.sql:303-310`).
- A derived streak is less error-prone than trying to keep a mutable counter consistent after imports, backfills, or manual edits.

### Decision 3: Keep the implementation inside the existing `lute.stats` package, but split page routes from API/service code
Extend the current stats package instead of inventing a new feature package.

Why:
- The stats blueprint is already registered and wired (`lute/app_factory.py:65`, `lute/app_factory.py:351`).
- The existing stats page already proves the template + Chart.js delivery path (`lute/stats/routes.py:12-23`, `lute/templates/stats/index.html:9-155`).

## Proposed Database Design

### 1) `reading_sessions`
Purpose: canonical activity fact table for dashboard analytics.

Suggested columns:
- `RsID` INTEGER PK
- `RsLgID` INTEGER NOT NULL FK -> `languages.LgID`
- `RsBkID` INTEGER NULL FK -> `books.BkID`
- `RsTxID` INTEGER NULL FK -> `texts.TxID`
- `RsStartedAt` DATETIME NOT NULL
- `RsEndedAt` DATETIME NULL
- `RsSource` VARCHAR(20) NOT NULL  
  values: `mark_read`, `page_open`, `legacy_backfill`
- `RsWordsRead` INTEGER NOT NULL DEFAULT 0
- `RsPagesRead` INTEGER NOT NULL DEFAULT 0
- `RsDurationSeconds` INTEGER NULL
- `RsCreatedAt` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP

Indexes:
- `(RsLgID, RsStartedAt)` for overview/streak/heatmap
- `(RsBkID, RsStartedAt)` for per-book completion charts
- `(RsTxID)` for debugging and joins back to page history
- `(date(RsStartedAt))` is not directly indexable in portable SQLAlchemy, so prefer raw timestamp index plus date bucketing in query SQL

Backfill strategy:
- Seed one `reading_sessions` row per existing `wordsread` row using `WrReadDate`, `WrWordCount`, `WrLgID`, and joined `texts.TxBkID` where possible (`lute/db/schema/baseline.sql:206-215`).
- Keep the original `wordsread` rows untouched.

### 2) `goals`
Purpose: user-configured targets for reading and vocabulary.

Suggested columns:
- `GlID` INTEGER PK
- `GlScopeType` VARCHAR(20) NOT NULL  
  values: `global`, `language`, `book`
- `GlScopeID` INTEGER NULL  
  stores `LgID` or `BkID` depending on scope type
- `GlMetric` VARCHAR(30) NOT NULL  
  values: `words_read`, `pages_read`, `books_completed`, `known_words`, `streak_days`
- `GlCadence` VARCHAR(20) NOT NULL  
  values: `daily`, `weekly`, `monthly`, `all_time`
- `GlTargetValue` INTEGER NOT NULL
- `GlStartDate` DATE NOT NULL
- `GlEndDate` DATE NULL
- `GlIsActive` BOOLEAN NOT NULL DEFAULT 1
- `GlTitle` VARCHAR(120) NOT NULL
- `GlCreatedAt` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP

Indexes:
- `(GlIsActive, GlMetric, GlCadence)`
- `(GlScopeType, GlScopeID)`

### 3) `milestones`
Purpose: named thresholds tied to a goal or progress stream.

Suggested columns:
- `MsID` INTEGER PK
- `MsGoalID` INTEGER NULL FK -> `goals.GlID`
- `MsMetric` VARCHAR(30) NOT NULL
- `MsThresholdValue` INTEGER NOT NULL
- `MsTitle` VARCHAR(120) NOT NULL
- `MsDescription` TEXT NULL
- `MsReachedAt` DATETIME NULL
- `MsDisplayOrder` INTEGER NOT NULL DEFAULT 0
- `MsCreatedAt` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP

Indexes:
- `(MsGoalID, MsThresholdValue)`
- `(MsMetric, MsReachedAt)`

### Integration rules with existing schema
- Use `books.BkReadingStatus` (`lute/models/book.py:52`, `lute/book/routes.py:314-339`) as the human-maintained lifecycle state.
- Use `texts.TxWordCount`, `texts.TxReadDate`, and `wordsread.WrWordCount` as the historical reading backbone (`lute/models/book.py:177-180`, `lute/models/book.py:301-302`).
- Use `words.WoStatus`, `WoCreated`, and `WoStatusChanged` for vocabulary distribution and trend endpoints (`lute/models/term.py:103-107`, `lute/db/schema/baseline.sql:128-130`, `lute/db/schema/baseline.sql:292-310`).

## API Plan

Implement API routes under `/api/stats` while preserving existing `/stats` for backward compatibility during rollout.

### Route structure
Recommended file shape:
- `lute/stats/routes.py` — HTML routes only (`/stats`, `/progress`)
- `lute/stats/api_routes.py` — JSON endpoints under a second blueprint with `url_prefix='/api/stats'`
- `lute/stats/service.py` — orchestration/service layer
- `lute/stats/queries.py` — raw SQL / aggregation helpers
- `lute/stats/serializers.py` — response shaping helpers if needed

This keeps Flask views thin and avoids overgrowing the current `lute/stats/service.py:9-96` single-file implementation.

### `/api/stats/overview`
Purpose: top-of-dashboard summary and heatmap source.

Response shape:
- `summary`: total words read, total sessions, current streak, best streak, active goals count
- `heatmap`: array of `{date, words_read, sessions}` for last 365 days
- `languages`: optional summary by language for filter chips
- `goals`: active goal snapshots with current progress percentage

Primary data sources:
- `reading_sessions`
- fallback historical totals from `wordsread` during backfill transition
- `goals` / `milestones`

### `/api/stats/books`
Purpose: book completion bars and per-book progress cards.

Response shape:
- array of books with:
  - `book_id`
  - `title`
  - `language`
  - `reading_status`
  - `pages_total`
  - `pages_read`
  - `words_total`
  - `words_read`
  - `completion_percent`
  - `last_activity_at`

Derivation:
- `pages_total` / `words_total` from `texts` (`lute/book/datatables.py:18-38` already computes similar aggregates)
- `pages_read` from `texts.TxReadDate is not null`
- `words_read` from summed `reading_sessions.RsWordsRead` or legacy `wordsread.WrWordCount`
- `reading_status` from `books.BkReadingStatus`

### `/api/stats/vocabulary`
Purpose: vocabulary distribution and vocabulary-over-time chart.

Response shape:
- `distribution`: counts by `WoStatus`
- `summary`: known / learning / unknown / ignored totals
- `timeline`: cumulative known-word counts by date
- optional `by_language`

Derivation:
- current distribution from `words.WoStatus`
- cumulative-known trend from `WoCreated` for terms no longer unknown, because the trigger updates `WoCreated` when a term leaves status 0 (`lute/db/schema/baseline.sql:303-310`)
- if precise “status churn over time” later becomes necessary, add a future `vocabulary_events` table, but do **not** scope-creep this initial delivery

### `/api/stats/streak`
Purpose: streak card and streak detail.

Response shape:
- `current_streak_days`
- `best_streak_days`
- `today_complete`
- `last_active_date`
- `daily_activity`: compact trailing 30–90 day series for sparkline/debugging

Derivation:
- compute from distinct local dates with activity in `reading_sessions` or `wordsread`
- define “active day” as any date with `sum(words_read) > 0`

## Frontend Plan (`/progress`)

### Route and template
Add a new HTML route:
- `GET /progress` -> `lute/templates/progress/index.html`

Keep existing `/stats/` intact initially so the new dashboard can ship incrementally without breaking the current statistics page (`lute/stats/routes.py:12-23`).

### Navigation integration
Update `lute/templates/base.html:126-130` so the About menu includes `Progress Dashboard` (or replace `Statistics` with `Progress`).

### Static assets
Recommended files:
- `lute/static/js/progress-dashboard.js`
- `lute/static/css/progress-dashboard.css`
- optional shared helper `lute/static/js/chart-helpers.js` if repeated chart config emerges

### Page composition
1. **KPI row**
   - current streak
   - best streak
   - words read today / this week
   - active goals
2. **Vocabulary chart**
   - doughnut or horizontal stacked bar for current distribution by status
   - small line chart for cumulative known words over time
3. **Books chart**
   - horizontal bar chart ordered by completion percent descending
4. **Reading heatmap**
   - lightweight custom grid rendered from `/api/stats/overview` heatmap payload
   - Chart.js is poor for GitHub-style heatmaps; use DOM/CSS grid instead of forcing Chart.js
5. **Streak card / sparkline**
   - numeric counter plus 30-day activity sparkline from `/api/stats/streak`

### Chart.js usage guidance
Use Chart.js only where it fits well:
- vocabulary distribution -> doughnut/stacked bar
- book completion -> horizontal bar
- streak sparkline -> line
- heatmap -> custom HTML/CSS, not Chart.js

That keeps the frontend cleaner than trying to coerce Chart.js into calendar layout, despite existing Chart.js use in `lute/templates/stats/index.html:83-153`.

## Implementation Steps

1. **Add schema + ORM models**
   - add migration SQL files under `lute/db/schema/migrations/`
   - update baseline schema if the project’s migration workflow requires it, consistent with existing baseline + migration files (`lute/db/schema/baseline.sql:167-215`)
   - add ORM models in a new file such as `lute/models/progress.py`
   - export them from `lute/models/__init__.py` if needed

2. **Backfill and data-write integration**
   - write migration SQL to backfill `reading_sessions` from `wordsread`
   - extend `lute/read/service.py:83-94` so new page-read actions write both legacy `WordsRead` and new `ReadingSession`
   - optionally capture `page_open` sessions from `lute/read/service.py:162-164` only if the UI semantics are clear; otherwise defer and keep MVP to explicit read completions

3. **Build stats query/service layer**
   - refactor `lute/stats/service.py` into composable functions or helper modules
   - implement aggregation functions for overview/books/vocabulary/streak
   - keep query logic SQL-heavy and response shaping Python-light for SQLite efficiency

4. **Add API blueprint and routes**
   - create `/api/stats/overview`, `/api/stats/books`, `/api/stats/vocabulary`, `/api/stats/streak`
   - register new blueprint from `lute/app_factory.py:340-352` alongside the existing stats blueprint
   - keep response contracts stable and versionable

5. **Add `/progress` page and assets**
   - create `lute/templates/progress/index.html`
   - create dedicated JS/CSS assets
   - fetch all four endpoints client-side and render KPI cards/charts/heatmap

6. **Integrate navigation and rollout path**
   - update `lute/templates/base.html:126-130`
   - decide whether `/stats/` stays as legacy page, redirects to `/progress`, or links forward
   - preserve existing `/book/table_stats/<id>` behavior used by the books listing (`lute/book/routes.py:295-311`, `lute/templates/book/tablelisting.html:253-313`)

7. **Test and verify**
   - migration/backfill tests
   - API contract tests
   - template smoke tests
   - service-level aggregation tests with realistic mixed data

## Acceptance Criteria

### Database
- Migration creates `reading_sessions`, `goals`, and `milestones` successfully on a clean database.
- Migration backfills `reading_sessions` from existing `wordsread` without deleting legacy history.
- New tables have indexes that support date-range, language, and book queries.

### Backend/API
- `GET /api/stats/overview` returns KPI + heatmap data with HTTP 200.
- `GET /api/stats/books` returns per-book completion payload with HTTP 200.
- `GET /api/stats/vocabulary` returns vocabulary distribution + timeline payload with HTTP 200.
- `GET /api/stats/streak` returns current/best streak data with HTTP 200.
- Existing `/stats/` and `/book/table_stats/<id>` flows still work.

### Frontend
- `GET /progress` renders successfully from the base template.
- The page displays a streak counter, vocabulary chart, book completion chart, and reading heatmap.
- The page handles empty-state datasets without JS errors.
- The navigation exposes the new dashboard entry.

### Data correctness
- Book completion uses existing `texts` page and word counts rather than duplicating totals.
- Vocabulary distribution matches current `words.WoStatus` counts.
- Streak calculations are based on distinct active dates, not raw row counts.

## Risks and Mitigations

1. **Risk: double-counting historical and new activity during backfill**
   - Mitigation: backfill once in migration with `RsSource='legacy_backfill'`; post-migration writes only come from runtime code.

2. **Risk: ambiguous “session” semantics**
   - Mitigation: define MVP `reading_sessions` as a normalized read-activity fact, initially one row per completed page-read event. Avoid premature duration/session-grouping complexity.

3. **Risk: vocabulary timeline may not represent every intermediate status change**
   - Mitigation: explicitly scope initial vocabulary trend to “known words over time” using `WoCreated`; defer full status-event history unless product requirements demand it.

4. **Risk: heatmap rendering complexity**
   - Mitigation: render heatmap with DOM/CSS grid, not Chart.js.

5. **Risk: stats code becomes another monolith**
   - Mitigation: split route, query, and serialization responsibilities instead of expanding `lute/stats/service.py:9-96` indefinitely.

## Verification Steps

1. Run migration against empty DB and existing populated DB.
2. Verify `reading_sessions` row counts match legacy `wordsread` backfill expectations.
3. Run targeted pytest coverage for:
   - migration/backfill
   - `mark_page_read` dual-write behavior
   - API payload structure
   - streak edge cases (no activity, today active, broken streak, best streak)
4. Load `/progress` in browser and verify:
   - no console errors
   - charts render with demo/fixture data
   - empty states render gracefully
5. Re-check existing pages:
   - `/stats/`
   - books listing async stats
   - `/read/<bookid>/page/<n>` mark-as-read flow

## Suggested Test Files

- `tests/orm/test_ProgressModels.py`
- `tests/unit/stats/test_progress_service.py`
- `tests/unit/stats/test_streak_calculation.py`
- `tests/unit/read/test_mark_page_read_progress_integration.py`
- `tests/ui/test_progress_dashboard.py` or equivalent route/template tests already used in repo

## Recommended Delivery Sequence

### Phase 1
Schema, ORM, backfill, and service/query layer.

### Phase 2
API routes + tests.

### Phase 3
`/progress` template, JS/CSS, and navigation integration.

### Phase 4
Refinement, empty states, visual polish, and optional `/stats -> /progress` redirect decision.
