"""
Progress tracking entities.
"""

from lute.db import db


class ReadingSession(db.Model):
    """
    Normalized reading activity used by the progress dashboard.
    """

    __tablename__ = "reading_sessions"

    id = db.Column("RsID", db.Integer, primary_key=True)
    language_id = db.Column(
        "RsLgID", db.Integer, db.ForeignKey("languages.LgID"), nullable=False
    )
    book_id = db.Column(
        "RsBkID",
        db.Integer,
        db.ForeignKey("books.BkID", ondelete="SET NULL"),
        nullable=True,
    )
    text_id = db.Column(
        "RsTxID",
        db.Integer,
        db.ForeignKey("texts.TxID", ondelete="SET NULL"),
        nullable=True,
    )
    started_at = db.Column("RsStartedAt", db.DateTime, nullable=False)
    ended_at = db.Column("RsEndedAt", db.DateTime, nullable=True)
    source = db.Column("RsSource", db.String(20), nullable=False, default="mark_read")
    words_read = db.Column("RsWordsRead", db.Integer, nullable=False, default=0)
    pages_read = db.Column("RsPagesRead", db.Integer, nullable=False, default=0)
    duration_seconds = db.Column("RsDurationSeconds", db.Integer, nullable=True)
    created_at = db.Column(
        "RsCreatedAt", db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )

    language = db.relationship("Language")
    book = db.relationship("Book")
    text = db.relationship("Text")

    @classmethod
    def from_text(
        cls,
        text,
        started_at,
        source="mark_read",
    ):
        "Build a reading session from a Text."
        session = cls()
        session.language_id = text.book.language.id
        session.book_id = text.book.id
        session.text_id = text.id
        session.started_at = started_at
        session.ended_at = started_at
        session.source = source
        session.words_read = text.word_count or 0
        session.pages_read = 1
        return session


class Goal(db.Model):
    """
    Progress targets shown on the dashboard.
    """

    __tablename__ = "goals"

    id = db.Column("GlID", db.Integer, primary_key=True)
    scope_type = db.Column("GlScopeType", db.String(20), nullable=False, default="global")
    scope_id = db.Column("GlScopeID", db.Integer, nullable=True)
    metric = db.Column("GlMetric", db.String(30), nullable=False)
    cadence = db.Column("GlCadence", db.String(20), nullable=False, default="all_time")
    target_value = db.Column("GlTargetValue", db.Integer, nullable=False)
    start_date = db.Column("GlStartDate", db.Date, nullable=False)
    end_date = db.Column("GlEndDate", db.Date, nullable=True)
    is_active = db.Column("GlIsActive", db.Boolean, nullable=False, default=True)
    title = db.Column("GlTitle", db.String(120), nullable=False)
    created_at = db.Column(
        "GlCreatedAt", db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )

    milestones = db.relationship(
        "Milestone",
        back_populates="goal",
        cascade="all, delete-orphan",
        order_by="Milestone.display_order",
    )


class Milestone(db.Model):
    """
    Milestones attached to goals.
    """

    __tablename__ = "milestones"

    id = db.Column("MsID", db.Integer, primary_key=True)
    goal_id = db.Column(
        "MsGoalID",
        db.Integer,
        db.ForeignKey("goals.GlID", ondelete="CASCADE"),
        nullable=True,
    )
    metric = db.Column("MsMetric", db.String(30), nullable=False)
    threshold_value = db.Column("MsThresholdValue", db.Integer, nullable=False)
    title = db.Column("MsTitle", db.String(120), nullable=False)
    description = db.Column("MsDescription", db.Text, nullable=True)
    reached_at = db.Column("MsReachedAt", db.DateTime, nullable=True)
    display_order = db.Column("MsDisplayOrder", db.Integer, nullable=False, default=0)
    created_at = db.Column(
        "MsCreatedAt", db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )

    goal = db.relationship("Goal", back_populates="milestones")
