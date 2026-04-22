"""
Progress dashboard service tests.
"""

from datetime import date, timedelta

from sqlalchemy import text

from lute.db import db
from lute.models.term import Term
from lute.stats.service import (
    _calculate_streaks,
    create_goal,
    get_books_progress_data,
    get_overview_data,
    get_streak_data,
    get_vocabulary_data,
)
from lute.book.model import Book, Repository as BookRepository
from lute.read.service import Service as ReadService


def _make_book(language, title, pages):
    "Create and save a multi-page book."
    book = Book()
    book.title = title
    book.language_id = language.id
    book.text = "\n---\n".join(pages)
    repo = BookRepository(db.session)
    dbbook = repo.add(book)
    repo.commit()
    return dbbook


def _add_term(language, text_value, status):
    "Create and save a term."
    term = Term(language, text_value)
    term.status = status
    db.session.add(term)
    db.session.commit()
    return term


def test_progress_tables_exist_after_app_setup(app_context):
    "Fresh test DB should include progress tables via migrations."
    sql = """
    select name from sqlite_master
    where type = 'table'
      and name in ('reading_sessions', 'goals', 'milestones')
    order by name
    """
    names = [row[0] for row in db.session.execute(text(sql)).all()]
    assert names == ["goals", "milestones", "reading_sessions"]


def test_calculate_streaks_handles_gap():
    "Current streak should break on gaps, best should remain."
    today = date(2026, 4, 1)
    actual = _calculate_streaks(
        ["2026-03-28", "2026-03-29", "2026-03-31", "2026-04-01"], today=today
    )
    assert actual["current_streak_days"] == 2
    assert actual["best_streak_days"] == 2
    assert actual["today_complete"] is True
    assert actual["last_active_date"] == "2026-04-01"


def test_progress_dashboard_service_data(english, spanish, app_context):
    "Smoke test for overview/books/vocabulary/streak outputs."
    english_book = _make_book(english, "English Reader", ["Dog cat.", "Bird fish."])
    spanish_book = _make_book(spanish, "Spanish Reader", ["Uno dos tres."])

    read_service = ReadService(db.session)
    read_service.mark_page_read(english_book.id, 1, False)
    read_service.mark_page_read(spanish_book.id, 1, False)

    _add_term(english, "dog", 5)
    _add_term(english, "cat", 3)
    _add_term(spanish, "uno", 99)

    goal = create_goal(
        db.session,
        title="Read 10 words this week",
        metric="words_read",
        target_value=10,
        start_date=date.today() - timedelta(days=6),
        cadence="weekly",
        milestones=[
            {"title": "Half way", "threshold_value": 5},
            {"title": "Done", "threshold_value": 10},
        ],
    )

    overview = get_overview_data(db.session)
    assert overview["summary"]["total_words_read"] > 0
    assert overview["summary"]["active_goals_count"] == 1
    assert overview["goals"][0]["id"] == goal.id
    assert len(overview["heatmap"]) >= 1

    books = get_books_progress_data(db.session)
    assert [book["title"] for book in books] == ["English Reader", "Spanish Reader"]
    assert books[0]["pages_total"] >= books[0]["pages_read"]
    assert books[0]["words_read"] >= 0

    vocabulary = get_vocabulary_data(db.session)
    distribution = {row["status"]: row["count"] for row in vocabulary["distribution"]}
    assert distribution[3] >= 1
    assert distribution[5] >= 1
    assert distribution[99] >= 1
    assert vocabulary["summary"]["total"] >= 3

    streak = get_streak_data(db.session)
    assert streak["current_streak_days"] >= 1
    assert streak["best_streak_days"] >= 1
    assert len(streak["daily_activity"]) >= 1
