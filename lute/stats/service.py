"""
Calculating stats.
"""

from datetime import date, datetime, timedelta
from sqlalchemy import text

from lute.models.progress import Goal, Milestone


STATUS_LABELS = {
    0: "Unknown",
    1: "New (1)",
    2: "New (2)",
    3: "Learning (3)",
    4: "Learning (4)",
    5: "Learned",
    98: "Ignored",
    99: "Well Known",
}


def _date_to_string(value):
    "Return date/datetime as yyyy-mm-dd, or None."
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return value.strftime("%Y-%m-%d")


def _datetime_to_string(value):
    "Return datetime as iso-like string, or None."
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _get_data_per_lang(session):
    "Return dict of lang name to dict[date_yyyymmdd}: count"
    ret = {}
    sql = """
    select lang, dt, sum(WrWordCount) as count
    from (
      select LgName as lang, strftime('%Y-%m-%d', WrReadDate) as dt, WrWordCount
      from wordsread
      inner join languages on LgID = WrLgID
    ) raw
    group by lang, dt
    order by lang, dt
    """
    result = session.execute(text(sql)).all()
    for row in result:
        langname = row[0]
        if langname not in ret:
            ret[langname] = {}
        ret[langname][row[1]] = int(row[2])
    return ret


def _charting_data(readbydate):
    "Calc data and running total."
    dates = sorted(readbydate.keys())
    if len(dates) == 0:
        return []

    first_date = datetime.strptime(dates[0], "%Y-%m-%d")
    day_before_first = first_date - timedelta(days=1)
    dbf = day_before_first.strftime("%Y-%m-%d")
    data = [{"readdate": dbf, "wordcount": 0, "runningTotal": 0}]

    total = 0
    for d in dates:
        dcount = readbydate.get(d)
        total += dcount
        hsh = {"readdate": d, "wordcount": dcount, "runningTotal": total}
        data.append(hsh)
    return data


def get_chart_data(session):
    "Get data for chart for each language."
    raw_data = _get_data_per_lang(session)
    chartdata = {}
    for k, v in raw_data.items():
        chartdata[k] = _charting_data(v)
    return chartdata


def _readcount_by_date(readbydate):
    """
    Return data as array: [ today, week, month, year, all time ]
    """
    today = datetime.now().date()

    def _in_range(i):
        start_date = today - timedelta(days=i)
        dates = [
            start_date + timedelta(days=x) for x in range((today - start_date).days + 1)
        ]
        ret = 0
        for d in dates:
            df = d.strftime("%Y-%m-%d")
            ret += readbydate.get(df, 0)
        return ret

    return {
        "day": _in_range(0),
        "week": _in_range(6),
        "month": _in_range(29),
        "year": _in_range(364),
        "total": _in_range(3650),
    }


def get_table_data(session):
    "Wordcounts by lang in time intervals."
    raw_data = _get_data_per_lang(session)

    ret = []
    for langname, readbydate in raw_data.items():
        ret.append({"name": langname, "counts": _readcount_by_date(readbydate)})
    return ret


def _daily_reading_rows(session):
    "Daily reading totals from reading_sessions."
    sql = """
    select
      strftime('%Y-%m-%d', RsStartedAt) as dt,
      sum(RsWordsRead) as words_read,
      count(*) as session_count
    from reading_sessions
    group by dt
    order by dt
    """
    return session.execute(text(sql)).all()


def _daily_activity_data(session):
    "Daily reading rows serialized for APIs."
    return [
        {
            "date": row[0],
            "words_read": int(row[1] or 0),
            "sessions": int(row[2] or 0),
        }
        for row in _daily_reading_rows(session)
    ]


def _calculate_streaks(day_strings, today=None):
    "Calculate current/best streak from yyyy-mm-dd strings."
    if today is None:
        today = date.today()
    if not day_strings:
        return {
            "current_streak_days": 0,
            "best_streak_days": 0,
            "today_complete": False,
            "last_active_date": None,
        }

    active_days = sorted(datetime.strptime(d, "%Y-%m-%d").date() for d in set(day_strings))
    best = 0
    current_run = 0
    previous = None
    for active_day in active_days:
        if previous is None or active_day == previous + timedelta(days=1):
            current_run += 1
        else:
            current_run = 1
        best = max(best, current_run)
        previous = active_day

    active_day_set = set(active_days)
    current = 0
    cursor = today
    while cursor in active_day_set:
        current += 1
        cursor -= timedelta(days=1)

    return {
        "current_streak_days": current,
        "best_streak_days": best,
        "today_complete": today in active_day_set,
        "last_active_date": _date_to_string(active_days[-1]),
    }


def get_streak_data(session):
    "Return streak summary and recent daily activity."
    activity = _daily_activity_data(session)
    streaks = _calculate_streaks([row["date"] for row in activity])
    return {
        **streaks,
        "daily_activity": activity[-90:],
    }


def _goal_period_start(goal, today):
    "Return period start date for a goal."
    if goal.cadence == "daily":
        return today
    if goal.cadence == "weekly":
        return today - timedelta(days=6)
    if goal.cadence == "monthly":
        return today - timedelta(days=29)
    return goal.start_date


def _goal_words_progress(session, goal, today):
    "Words/pages goal progress from reading_sessions."
    metric_column = "RsWordsRead" if goal.metric == "words_read" else "RsPagesRead"
    period_start = _goal_period_start(goal, today)
    sql = f"""
    select coalesce(sum({metric_column}), 0)
    from reading_sessions
    where date(RsStartedAt) >= :period_start
    """
    params = {"period_start": _date_to_string(period_start)}

    if goal.end_date is not None:
        sql += " and date(RsStartedAt) <= :period_end"
        params["period_end"] = _date_to_string(goal.end_date)

    if goal.scope_type == "language":
        sql += " and RsLgID = :scope_id"
        params["scope_id"] = goal.scope_id
    elif goal.scope_type == "book":
        sql += " and RsBkID = :scope_id"
        params["scope_id"] = goal.scope_id

    return int(session.execute(text(sql), params).scalar() or 0)


def _goal_books_completed_progress(session, goal):
    "Book completion progress."
    sql = """
    select count(*)
    from books
    where BkArchived = 0
      and BkReadingStatus = 'completed'
    """
    params = {}
    if goal.scope_type == "language":
        sql += " and BkLgID = :scope_id"
        params["scope_id"] = goal.scope_id
    elif goal.scope_type == "book":
        sql += " and BkID = :scope_id"
        params["scope_id"] = goal.scope_id
    return int(session.execute(text(sql), params).scalar() or 0)


def _goal_known_words_progress(session, goal):
    "Known-word goal progress."
    sql = """
    select count(*)
    from words
    where WoStatus in (1, 2, 3, 4, 5, 99)
    """
    params = {}
    if goal.scope_type == "language":
        sql += " and WoLgID = :scope_id"
        params["scope_id"] = goal.scope_id
    return int(session.execute(text(sql), params).scalar() or 0)


def _goal_streak_progress(session, goal):
    "Streak goal progress."
    sql = """
    select strftime('%Y-%m-%d', RsStartedAt) as dt
    from reading_sessions
    where 1 = 1
    """
    params = {}
    if goal.scope_type == "language":
        sql += " and RsLgID = :scope_id"
        params["scope_id"] = goal.scope_id
    elif goal.scope_type == "book":
        sql += " and RsBkID = :scope_id"
        params["scope_id"] = goal.scope_id
    sql += " group by dt order by dt"
    rows = session.execute(text(sql), params).all()
    return _calculate_streaks([row[0] for row in rows])["current_streak_days"]


def _goal_progress_value(session, goal, today):
    "Return current progress for a goal."
    if goal.metric in ("words_read", "pages_read"):
        return _goal_words_progress(session, goal, today)
    if goal.metric == "books_completed":
        return _goal_books_completed_progress(session, goal)
    if goal.metric == "known_words":
        return _goal_known_words_progress(session, goal)
    if goal.metric == "streak_days":
        return _goal_streak_progress(session, goal)
    return 0


def _serialize_goal(session, goal, today):
    "Serialize a goal and attached milestones."
    current_value = _goal_progress_value(session, goal, today)
    progress_percent = 0
    if goal.target_value > 0:
        progress_percent = min(100, round((current_value * 100.0) / goal.target_value))

    milestones = []
    for milestone in goal.milestones:
        reached_at = milestone.reached_at
        if reached_at is None and current_value >= milestone.threshold_value:
            reached_at = today
        milestones.append(
            {
                "id": milestone.id,
                "title": milestone.title,
                "metric": milestone.metric,
                "threshold_value": milestone.threshold_value,
                "reached": current_value >= milestone.threshold_value,
                "reached_at": _date_to_string(reached_at)
                if not isinstance(reached_at, datetime)
                else _datetime_to_string(reached_at),
            }
        )

    return {
        "id": goal.id,
        "title": goal.title,
        "metric": goal.metric,
        "cadence": goal.cadence,
        "scope_type": goal.scope_type,
        "scope_id": goal.scope_id,
        "target_value": goal.target_value,
        "current_value": current_value,
        "progress_percent": progress_percent,
        "start_date": _date_to_string(goal.start_date),
        "end_date": _date_to_string(goal.end_date),
        "milestones": milestones,
    }


def get_overview_data(session):
    "Dashboard summary + heatmap + active goals."
    streak_data = get_streak_data(session)
    today = date.today()
    heatmap = [entry for entry in _daily_activity_data(session) if entry["date"] is not None]
    heatmap = heatmap[-365:]

    summary_sql = """
    select
      coalesce(sum(RsWordsRead), 0) as total_words,
      count(*) as total_sessions,
      coalesce(sum(case when date(RsStartedAt) = date('now') then RsWordsRead else 0 end), 0) as words_today,
      coalesce(sum(case when date(RsStartedAt) >= date('now', '-6 day') then RsWordsRead else 0 end), 0) as words_week
    from reading_sessions
    """
    summary_row = session.execute(text(summary_sql)).first()

    active_goals = (
        session.query(Goal)
        .filter(Goal.is_active == 1)
        .order_by(Goal.created_at.asc())
        .all()
    )
    goal_data = [_serialize_goal(session, goal, today) for goal in active_goals]

    language_sql = """
    select
      l.LgID,
      l.LgName,
      coalesce(sum(rs.RsWordsRead), 0) as words_read,
      count(rs.RsID) as session_count
    from languages l
    left join reading_sessions rs on rs.RsLgID = l.LgID
    group by l.LgID, l.LgName
    order by l.LgName
    """
    languages = []
    for row in session.execute(text(language_sql)).all():
        languages.append(
            {
                "language_id": int(row[0]),
                "name": row[1],
                "words_read": int(row[2] or 0),
                "sessions": int(row[3] or 0),
            }
        )

    return {
        "summary": {
            "total_words_read": int(summary_row[0] or 0),
            "total_sessions": int(summary_row[1] or 0),
            "words_today": int(summary_row[2] or 0),
            "words_this_week": int(summary_row[3] or 0),
            "current_streak_days": streak_data["current_streak_days"],
            "best_streak_days": streak_data["best_streak_days"],
            "active_goals_count": len(goal_data),
        },
        "heatmap": heatmap,
        "languages": languages,
        "goals": goal_data,
    }


def get_books_progress_data(session):
    "Per-book progress rows for the dashboard."
    sql = """
    select
      b.BkID,
      b.BkTitle,
      l.LgName,
      b.BkReadingStatus,
      tc.page_count,
      coalesce(rc.pages_read, 0) as pages_read,
      tc.word_count,
      coalesce(rs.words_read, 0) as words_read,
      rs.last_activity_at
    from books b
    inner join languages l on l.LgID = b.BkLgID
    inner join (
      select
        TxBkID,
        count(*) as page_count,
        coalesce(sum(TxWordCount), 0) as word_count
      from texts
      group by TxBkID
    ) tc on tc.TxBkID = b.BkID
    left join (
      select
        TxBkID,
        count(*) as pages_read
      from texts
      where TxReadDate is not null
      group by TxBkID
    ) rc on rc.TxBkID = b.BkID
    left join (
      select
        RsBkID,
        coalesce(sum(RsWordsRead), 0) as words_read,
        max(RsStartedAt) as last_activity_at
      from reading_sessions
      where RsBkID is not null
      group by RsBkID
    ) rs on rs.RsBkID = b.BkID
    where b.BkArchived = 0
    order by b.BkTitle
    """
    rows = []
    for row in session.execute(text(sql)).all():
        page_count = int(row[4] or 0)
        pages_read = int(row[5] or 0)
        completion_percent = 0
        if page_count > 0:
            completion_percent = round((pages_read * 100.0) / page_count)

        rows.append(
            {
                "book_id": int(row[0]),
                "title": row[1],
                "language": row[2],
                "reading_status": row[3],
                "pages_total": page_count,
                "pages_read": pages_read,
                "words_total": int(row[6] or 0),
                "words_read": int(row[7] or 0),
                "completion_percent": completion_percent,
                "last_activity_at": _datetime_to_string(row[8]),
            }
        )
    return rows


def get_vocabulary_data(session):
    "Vocabulary distribution and cumulative timeline."
    distribution = {status: 0 for status in STATUS_LABELS}
    distribution_sql = """
    select WoStatus, count(*)
    from words
    group by WoStatus
    """
    for row in session.execute(text(distribution_sql)).all():
        distribution[int(row[0])] = int(row[1] or 0)

    timeline_sql = """
    select
      strftime('%Y-%m-%d', WoCreated) as dt,
      count(*) as count
    from words
    where WoStatus in (1, 2, 3, 4, 5, 99)
    group by dt
    order by dt
    """
    running_total = 0
    timeline = []
    for row in session.execute(text(timeline_sql)).all():
        running_total += int(row[1] or 0)
        timeline.append(
            {
                "date": row[0],
                "count": int(row[1] or 0),
                "running_total": running_total,
            }
        )

    by_language_sql = """
    select
      l.LgID,
      l.LgName,
      count(w.WoID) as total_words,
      coalesce(sum(case when w.WoStatus in (1, 2, 3, 4, 5, 99) then 1 else 0 end), 0) as active_words
    from languages l
    left join words w on w.WoLgID = l.LgID
    group by l.LgID, l.LgName
    order by l.LgName
    """
    by_language = []
    for row in session.execute(text(by_language_sql)).all():
        by_language.append(
            {
                "language_id": int(row[0]),
                "name": row[1],
                "total_words": int(row[2] or 0),
                "active_words": int(row[3] or 0),
            }
        )

    return {
        "distribution": [
            {
                "status": status,
                "label": STATUS_LABELS[status],
                "count": distribution[status],
            }
            for status in sorted(STATUS_LABELS)
        ],
        "summary": {
            "unknown": distribution[0],
            "new": distribution[1] + distribution[2],
            "learning": distribution[3] + distribution[4],
            "learned": distribution[5] + distribution[99],
            "ignored": distribution[98],
            "total": sum(distribution.values()),
        },
        "timeline": timeline,
        "by_language": by_language,
    }


def get_goals_data(session):
    "Return active goals for the dashboard."
    today = date.today()
    goals = (
        session.query(Goal)
        .filter(Goal.is_active == 1)
        .order_by(Goal.created_at.asc())
        .all()
    )
    return [_serialize_goal(session, goal, today) for goal in goals]


def create_goal(
    session,
    title,
    metric,
    target_value,
    start_date,
    **kwargs,
):
    "Helper used by tests and future UI flows."
    goal = Goal()
    goal.title = title
    goal.metric = metric
    goal.target_value = target_value
    goal.start_date = start_date
    goal.cadence = kwargs.get("cadence", "all_time")
    goal.scope_type = kwargs.get("scope_type", "global")
    goal.scope_id = kwargs.get("scope_id")
    goal.end_date = kwargs.get("end_date")
    session.add(goal)
    session.flush()

    for index, milestone_data in enumerate(kwargs.get("milestones", []) or []):
        milestone = Milestone()
        milestone.goal = goal
        milestone.metric = milestone_data.get("metric", metric)
        milestone.threshold_value = milestone_data["threshold_value"]
        milestone.title = milestone_data["title"]
        milestone.description = milestone_data.get("description")
        milestone.display_order = milestone_data.get("display_order", index)
        session.add(milestone)

    session.commit()
    return goal
