Lute Progress Analytics Dashboard - Implementation Plan

CONTEXT:
Lute is a language learning app (https://github.com/jzohrab/lute) that helps users learn languages through reading. It tracks words, books, and reading progress.

EXISTING DATABASE SCHEMA:
- books: BkID, BkTitle, BkReadingStatus (not_started/reading/completed), BkCreated
- bookstats: distinctterms, distinctunknowns, unknownpercent, status_distribution (JSON)
- words: WoID, WoText, WoStatus (0-5, 98, 99), WoCreated, WoStatusChanged
- wordsread: WrID, WrReadDate, WrWordCount
- statuses: 0=Unknown, 1=New(1), 2=New(2), 3=Learning(3), 4=Learning(4), 5=Learned, 98=Ignored, 99=Well Known

FEATURES TO IMPLEMENT:

1. DASHBOARD API ENDPOINTS (Flask/Python)
   - GET /api/stats/overview - Total books, words, streak
   - GET /api/stats/daily - Daily word counts for last 30 days
   - GET /api/stats/books - Book progress with status breakdown
   - GET /api/stats/vocabulary - Word mastery distribution
   - GET /api/stats/streak - Current streak and history

2. FRONTEND (HTML/CSS/JS)
   - Dashboard page at /progress
   - Chart.js for visualizations:
     * Line chart: Daily words learned over time
     * Doughnut charts: Book completion status
     * Bar chart: Vocabulary mastery levels
     * Heatmap: Reading activity (GitHub-style)
   - Milestone badges section
   - Goal setting UI

3. NEW DATABASE TABLES
   - reading_sessions: session date, book_id, words_read, duration_minutes
   - user_goals: goal_type, target_value, deadline, current_value
   - user_milestones: milestone_type, achieved_date

4. STREAK CALCULATION LOGIC
   - Query wordsread table for distinct reading dates
   - Count consecutive days from today backwards
   - Show "current streak" and "longest streak"

5. MASTERY SCORE ALGORITHM
   - Weighted score: Unknown(0) + New(1-2)*10 + Learning(3-4)*50 + Learned(5)*100 + WellKnown(99)*100
   - Max score = total_words * 100
   - Mastery % = current_score / max_score

6. MILESTONE BADGES
   - "Getting Started" - First word marked as learned
   - "Century" - 100 words learned
   - "Book Worm" - First book completed
   - "Polyglot" - Reading in 2+ languages
   - "Streak Master" - 7-day streak
   - "Dedicated" - 30-day streak
   - "Speed Reader" - Read 1000 words in one session

TECHNICAL STACK:
- Backend: Flask (extends existing Lute Flask app)
- Frontend: Chart.js, vanilla JS, CSS Grid/Flexbox
- Charts: Chart.js (CDN)
- Icons: Font Awesome or SVG badges
- Database: SQLite (existing)

INTEGRATION POINTS:
- Add route in lute/routes.py
- Add template in lute/templates/
- Add static files in lute/static/
- Update navigation to include Progress link
- Create database migration script

FILE STRUCTURE:
lute/
  routes/
    progress.py          # New dashboard routes
  templates/
    progress/
      dashboard.html     # Main dashboard template
      badges.html        # Milestones view
      goals.html         # Goal setting page
  static/
    css/
      progress.css       # Dashboard styles
    js/
      progress.js        # Charts and interactivity
  models/
    reading_session.py   # New model
    user_goal.py         # New model
    milestone.py         # New model

Acceptance Criteria:
- User can view overall progress at /progress
- Charts update from real database data
- Streak is calculated correctly from reading history
- Badges appear when milestones are achieved
- Page is responsive and visually appealing
- No performance issues with 1000s of words
