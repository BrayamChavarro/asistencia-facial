import datetime
from fastapi import APIRouter
from sqlalchemy import func
from app.database import Attendance, User, get_session

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary():
    db = get_session()
    try:
        today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + datetime.timedelta(days=1)

        total_users = db.query(func.count(User.id)).filter(User.active == 1).scalar() or 0

        today_attendances = db.query(func.count(Attendance.id)).filter(
            Attendance.timestamp >= today_start, Attendance.timestamp < today_end
        ).scalar() or 0

        today_entries = db.query(func.count(Attendance.id)).filter(
            Attendance.timestamp >= today_start, Attendance.timestamp < today_end,
            Attendance.type == "entry"
        ).scalar() or 0

        today_exits = db.query(func.count(Attendance.id)).filter(
            Attendance.timestamp >= today_start, Attendance.timestamp < today_end,
            Attendance.type == "exit"
        ).scalar() or 0

        today_users_raw = (
            db.query(
                Attendance.user_id,
                User.name,
                func.min(Attendance.timestamp).label("first_in"),
                func.max(Attendance.timestamp).label("last_out"),
                func.count(Attendance.id).label("total_marks"),
            )
            .join(User, Attendance.user_id == User.id)
            .filter(Attendance.timestamp >= today_start, Attendance.timestamp < today_end)
            .group_by(Attendance.user_id, User.name)
            .order_by(func.min(Attendance.timestamp))
            .all()
        )

        today_users = [
            {
                "user_id": u_id,
                "user_name": name,
                "entry": first_in.isoformat() if first_in else None,
                "exit": last_out.isoformat() if last_out else None,
                "total_marks": total_marks,
            }
            for u_id, name, first_in, last_out, total_marks in today_users_raw
        ]

        week_start = today_start - datetime.timedelta(days=datetime.datetime.utcnow().weekday())
        weekly_raw = (
            db.query(
                func.date(Attendance.timestamp).label("day"),
                func.count(func.distinct(Attendance.user_id)).label("unique_users"),
                func.count(Attendance.id).label("marks"),
            )
            .filter(Attendance.timestamp >= week_start)
            .group_by(func.date(Attendance.timestamp))
            .order_by(func.date(Attendance.timestamp))
            .all()
        )

        weekly = [
            {"day": day, "unique_users": uq, "marks": mk}
            for day, uq, mk in weekly_raw
        ]

        return {
            "total_users": total_users,
            "today_attendances": today_attendances,
            "today_entries": today_entries,
            "today_exits": today_exits,
            "today_users": today_users,
            "weekly": weekly,
        }
    finally:
        db.close()
