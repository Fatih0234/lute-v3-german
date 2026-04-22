# Test Spec: Lute Progress Dashboard

## Scope
Covers schema migrations, progress data backfill, API contracts, and the `/progress` dashboard rendering path.

## Unit Tests

1. **Streak calculation**
   - no sessions => current/best streak = 0
   - isolated active day => streak = 1
   - consecutive days => expected streak length
   - gap breaks streak
   - multiple sessions on same day count as one streak day

2. **Vocabulary aggregation**
   - current distribution matches `words.WoStatus`
   - known-word timeline uses non-unknown vocabulary timestamps consistently
   - ignored / well-known bucket mapping is stable if UI combines statuses

3. **Book aggregation**
   - completion percent = pages_read / pages_total
   - words_total derives from `texts.TxWordCount`
   - words_read derives from session/read events without double counting

## Integration Tests

1. **Migration / backfill**
   - migrating an existing DB creates new tables
   - `reading_sessions` backfill count equals legacy `wordsread` count
   - joined `book_id` values populate when `WrTxID` still points to a text

2. **Read flow integration**
   - marking a page read still inserts into `wordsread`
   - marking a page read also inserts into `reading_sessions`
   - existing term/book behavior remains unchanged

3. **API routes**
   - `/api/stats/overview` returns JSON with `summary` and `heatmap`
   - `/api/stats/books` returns array items with completion fields
   - `/api/stats/vocabulary` returns `distribution` and `timeline`
   - `/api/stats/streak` returns streak summary fields

## UI / Route Tests

1. `/progress` returns 200 and includes dashboard mount nodes.
2. Base navigation includes a link to the dashboard.
3. Empty-state payloads do not break the page.
4. Demo data or seeded fixtures render at least one chart and one KPI card.

## Regression Checks

1. `/stats/` continues to load.
2. `/book/table_stats/<id>` still returns status distribution JSON.
3. Marking a page read still updates prior behavior around `TxReadDate` and `wordsread`.

## Manual Verification

1. Open `/progress` and confirm:
   - streak card displays
   - vocabulary chart displays
   - book bars display
   - heatmap cells render for active dates
2. Mark another page as read and refresh dashboard.
3. Confirm totals update without affecting existing book stats UI.
