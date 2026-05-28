from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Header, Query
from app.database import User, Attendance, get_session
from app.schemas import UserResponse, RegisterResult, UserDetailResponse, AttendanceResponse, UserPhotosResponse
from app.face_engine import register_face, invalidate_cache
from app.config import ADMIN_PIN
import datetime

router = APIRouter(prefix="/api/users", tags=["users"])


def verify_pin(x_admin_pin: str = Header("")):
    if x_admin_pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="PIN incorrecto")
    return True


@router.get("/", response_model=list[UserResponse])
def list_users():
    db = get_session()
    try:
        return db.query(User).filter(User.active == 1).all()
    finally:
        db.close()


@router.post("/register", response_model=RegisterResult)
async def register_user(
    name: str = Form(...),
    email: str = Form(""),
    image: UploadFile = File(...),
    x_admin_pin: str = Header(""),
):
    verify_pin(x_admin_pin)
    img_bytes = await image.read()
    result = register_face(img_bytes)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    email_val = email.strip() if email else None
    db = get_session()
    try:
        user = User(name=name, email=email_val, embedding=result["embedding_str"])
        db.add(user)
        db.commit()
        db.refresh(user)
        invalidate_cache()
        return RegisterResult(success=True, user_id=user.id, message=f"Usuario '{name}' registrado correctamente")
    finally:
        db.close()


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    x_admin_pin: str = Header(""),
):
    verify_pin(x_admin_pin)
    db = get_session()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        user.active = 0
        db.commit()
        invalidate_cache()
        return {"success": True, "message": "Usuario desactivado"}
    finally:
        db.close()


@router.get("/{user_id}", response_model=UserDetailResponse)
def user_detail(user_id: int):
    db = get_session()
    try:
        user = db.query(User).filter(User.id == user_id, User.active == 1).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_atts = (
            db.query(Attendance)
            .filter(Attendance.user_id == user_id, Attendance.timestamp >= today_start)
            .order_by(Attendance.timestamp.asc())
            .all()
        )
        recent_atts = (
            db.query(Attendance)
            .filter(Attendance.user_id == user_id)
            .order_by(Attendance.timestamp.desc())
            .limit(20)
            .all()
        )
        total = db.query(Attendance).filter(Attendance.user_id == user_id).count()

        def to_resp(a):
            return AttendanceResponse(
                id=a.id,
                user_id=a.user_id,
                user_name=user.name,
                timestamp=a.timestamp,
                confidence=a.confidence,
                type=a.type,
                photo_url=f"/uploads/{a.image_path}" if a.image_path else None,
            )

        return UserDetailResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            active=user.active,
            total_attendances=total,
            today_attendances=[to_resp(a) for a in today_atts],
            recent_attendances=[to_resp(a) for a in recent_atts],
        )
    finally:
        db.close()


@router.get("/{user_id}/photos", response_model=list[UserPhotosResponse])
def user_photos(
    user_id: int,
    days: int = Query(7, le=30),
):
    db = get_session()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        records = (
            db.query(Attendance)
            .filter(Attendance.user_id == user_id, Attendance.timestamp >= since)
            .order_by(Attendance.timestamp.asc())
            .all()
        )

        daily: dict[str, dict] = {}
        for a in records:
            day = a.timestamp.strftime("%Y-%m-%d")
            if day not in daily:
                daily[day] = {"entry": None, "exit": None, "entry_conf": None, "exit_conf": None}
            if a.type == "entry" and daily[day]["entry"] is None:
                daily[day]["entry"] = f"/uploads/{a.image_path}" if a.image_path else None
                daily[day]["entry_conf"] = a.confidence
            elif a.type == "exit" and daily[day]["exit"] is None:
                daily[day]["exit"] = f"/uploads/{a.image_path}" if a.image_path else None
                daily[day]["exit_conf"] = a.confidence

        return [
            UserPhotosResponse(
                date=day,
                entry=data["entry"],
                exit=data["exit"],
                entry_confidence=data["entry_conf"],
                exit_confidence=data["exit_conf"],
            )
            for day, data in sorted(daily.items(), reverse=True)
        ]
    finally:
        db.close()
