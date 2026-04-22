"""
/api/stats endpoints.
"""

from flask import Blueprint, jsonify

from lute.db import db
from lute.stats.service import (
    get_overview_data,
    get_books_progress_data,
    get_vocabulary_data,
    get_streak_data,
)


bp = Blueprint("stats_api", __name__, url_prefix="/api/stats")


@bp.route("/overview")
def overview():
    "Dashboard summary."
    return jsonify(get_overview_data(db.session))


@bp.route("/books")
def books():
    "Book progress cards."
    return jsonify(get_books_progress_data(db.session))


@bp.route("/vocabulary")
def vocabulary():
    "Vocabulary charts."
    return jsonify(get_vocabulary_data(db.session))


@bp.route("/streak")
def streak():
    "Streak data."
    return jsonify(get_streak_data(db.session))
