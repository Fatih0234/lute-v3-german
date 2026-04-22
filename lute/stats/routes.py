"""
/stats endpoints.
"""

from flask import Blueprint, render_template, jsonify
from lute.stats.service import get_chart_data, get_table_data
from lute.db import db

bp = Blueprint("stats", __name__, url_prefix="/stats")
progress_bp = Blueprint("progress", __name__)


@bp.route("/")
def index():
    "Main page."
    read_table_data = get_table_data(db.session)
    return render_template("stats/index.html", read_table_data=read_table_data)


@progress_bp.route("/progress")
def progress():
    "Progress dashboard."
    return render_template("progress/index.html")


@bp.route("/data")
def get_data():
    "Ajax call."
    chartdata = get_chart_data(db.session)
    return jsonify(chartdata)
