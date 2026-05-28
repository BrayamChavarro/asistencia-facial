import uuid
import os
import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from app.database import Attendance, User, get_session
from app.schemas import AttendanceResponse, RecognitionResult
from app.face_engine import extract_embedding, compare_embeddings, str_to_embedding, get_cached_embeddings
from app.config import UPLOAD_DIR
from typing import Optional

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.post("/mark", response_model=RecognitionResult)
async def mark_attendance(image: UploadFile = File(...)):
    img_bytes = await image.read()
    result = extract_embedding(img_bytes)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    embedding = result["embedding"]
    db = get_session()
    try:
        users = db.query(User).filter(User.active == 1).all()
        stored = get_cached_embeddings(users)
        match = compare_embeddings(embedding, stored)
        if not match:
            return RecognitionResult(success=False, message="Rostro no reconocido")

        today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.query(Attendance).filter(
            Attendance.user_id == match["user_id"],
            Attendance.timestamp >= today_start,
        ).count()

        att_type = "entry" if today_count == 0 else "exit"

        filename = f"{match['user_id']}_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(img_bytes)
        attendance = Attendance(
            user_id=match["user_id"],
            confidence=match["confidence"],
            image_path=filename,
            type=att_type,
        )
        db.add(attendance)
        db.commit()
        type_label = "Entrada" if att_type == "entry" else "Salida"
        return RecognitionResult(
            success=True,
            user_id=match["user_id"],
            user_name=match["user_name"],
            confidence=match["confidence"],
            message=f"{type_label} registrada: {match['user_name']}",
            type=att_type,
            photo_url=f"/uploads/{filename}",
        )
    finally:
        db.close()


@router.get("/today", response_model=list[AttendanceResponse])
def today_attendances():
    db = get_session()
    try:
        today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        records = (
            db.query(Attendance, User.name)
            .join(User, Attendance.user_id == User.id)
            .filter(Attendance.timestamp >= today_start)
            .order_by(Attendance.timestamp.desc())
            .all()
        )
        return [
            AttendanceResponse(
                id=a.id,
                user_id=a.user_id,
                user_name=name,
                timestamp=a.timestamp,
                confidence=a.confidence,
                type=a.type,
                photo_url=f"/uploads/{a.image_path}" if a.image_path else None,
            )
            for a, name in records
        ]
    finally:
        db.close()


@router.get("/history", response_model=list[AttendanceResponse])
def attendance_history(
    user_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
):
    db = get_session()
    try:
        q = db.query(Attendance, User.name).join(User, Attendance.user_id == User.id)
        if user_id:
            q = q.filter(Attendance.user_id == user_id)
        q = q.order_by(Attendance.timestamp.desc()).limit(limit)
        return [
            AttendanceResponse(
                id=a.id,
                user_id=a.user_id,
                user_name=name,
                timestamp=a.timestamp,
                confidence=a.confidence,
                type=a.type,
                photo_url=f"/uploads/{a.image_path}" if a.image_path else None,
            )
            for a, name in q.all()
        ]
    finally:
        db.close()
