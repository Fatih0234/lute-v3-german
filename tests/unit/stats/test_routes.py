"""
Progress and stats route tests.
"""

from lute.db import db
from lute.book.model import Book, Repository as BookRepository
from lute.read.service import Service as ReadService


def _make_book(language, title, text_value):
    "Create and save a single-page book."
    book = Book()
    book.title = title
    book.language_id = language.id
    book.text = text_value
    repo = BookRepository(db.session)
    dbbook = repo.add(book)
    repo.commit()
    return dbbook


def test_progress_page_renders(client, app_context):
    "Progress page should load."
    response = client.get("/progress")
    assert response.status_code == 200
    assert b"Progress" in response.data
    assert b"progress-dashboard" in response.data


def test_progress_api_endpoints_return_json(client, english, app_context):
    "Dashboard APIs should respond."
    book = _make_book(english, "Reader", "Dog cat.")
    ReadService(db.session).mark_page_read(book.id, 1, False)

    overview = client.get("/api/stats/overview")
    assert overview.status_code == 200
    assert "summary" in overview.get_json()

    books = client.get("/api/stats/books")
    assert books.status_code == 200
    assert isinstance(books.get_json(), list)

    vocabulary = client.get("/api/stats/vocabulary")
    assert vocabulary.status_code == 200
    assert "distribution" in vocabulary.get_json()

    streak = client.get("/api/stats/streak")
    assert streak.status_code == 200
    assert "current_streak_days" in streak.get_json()


def test_base_navigation_includes_progress_link(client, app_context):
    "Top navigation should include the progress dashboard."
    response = client.get("/")
    assert response.status_code == 200
    assert b"/progress" in response.data
