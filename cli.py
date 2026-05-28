"""
CLI - Asistencia Facial con reconocimiento facial por terminal/OpenCV.
Uso:
  python cli.py register      Registrar un nuevo usuario
  python cli.py attendance    Marcar asistencia
  python cli.py today         Ver asistencias de hoy
  python cli.py users         Listar usuarios registrados
"""

import sys
import cv2
import numpy as np
from app.database import init_db, Attendance, User, get_session
from app.face_engine import (
    register_face,
    extract_embedding,
    compare_embeddings,
    str_to_embedding,
    get_cached_embeddings,
)
from app.config import UPLOAD_DIR
import datetime
import uuid
import os


def capture_face(prompt: str = "Presiona ESPACIO para capturar, ESC para salir") -> np.ndarray | None:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: No se pudo abrir la cámara")
        return None
    print(f"[INFO] {prompt}")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.putText(frame, prompt, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("Asistencia Facial - CLI", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 32:
            cv2.destroyAllWindows()
            cap.release()
            return frame
        if key == 27:
            cv2.destroyAllWindows()
            cap.release()
            return None


def cmd_register():
    name = input("Nombre del usuario: ").strip()
    if not name:
        print("Nombre requerido")
        return
    email = input("Email (opcional): ").strip() or None
    img = capture_face("Mira a la cámara y presiona ESPACIO para registrar")
    if img is None:
        print("Registro cancelado")
        return
    result = register_face(img)
    if not result["success"]:
        print(f"ERROR: {result['error']}")
        return
    db = get_session()
    user = User(name=name, email=email, embedding=result["embedding_str"])
    db.add(user)
    db.commit()
    db.close()
    print(f"✅ Usuario '{name}' registrado correctamente (ID: {user.id})")


def cmd_attendance():
    img = capture_face("Mira a la cámara para marcar asistencia - ESPACIO para capturar")
    if img is None:
        print("Operación cancelada")
        return
    result = extract_embedding(img)
    if not result["success"]:
        print(f"ERROR: {result['error']}")
        return
    embedding = result["embedding"]
    db = get_session()
    users = db.query(User).filter(User.active == 1).all()
    stored = get_cached_embeddings(users)
    match = compare_embeddings(embedding, stored)
    if not match:
        db.close()
        print("❌ Rostro no reconocido")
        return

    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = db.query(Attendance).filter(
        Attendance.user_id == match["user_id"],
        Attendance.timestamp >= today_start,
    ).count()

    att_type = "entry" if today_count == 0 else "exit"
    type_label = "Entrada" if att_type == "entry" else "Salida"

    filename = f"{match['user_id']}_{uuid.uuid4().hex}.jpg"
    cv2.imwrite(os.path.join(UPLOAD_DIR, filename), img)
    attendance = Attendance(
        user_id=match["user_id"],
        confidence=match["confidence"],
        image_path=filename,
        type=att_type,
    )
    db.add(attendance)
    db.commit()
    db.close()
    print(f"✅ {type_label} registrada: {match['user_name']} (confianza: {match['confidence']:.2%})")


def cmd_today():
    db = get_session()
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    records = (
        db.query(Attendance, User.name)
        .join(User, Attendance.user_id == User.id)
        .filter(Attendance.timestamp >= today_start)
        .order_by(Attendance.timestamp.desc())
        .all()
    )
    db.close()
    if not records:
        print("No hay asistencias hoy")
        return
    print(f"\n{'ID':<5} {'Usuario':<20} {'Hora':<20} {'Confianza':<10}")
    print("-" * 55)
    for a, name in records:
        t = a.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        conf = f"{a.confidence:.2%}" if a.confidence else "N/A"
        print(f"{a.user_id:<5} {name:<20} {t:<20} {conf:<10}")


def cmd_users():
    db = get_session()
    users = db.query(User).filter(User.active == 1).all()
    db.close()
    if not users:
        print("No hay usuarios registrados")
        return
    print(f"\n{'ID':<5} {'Nombre':<25} {'Email':<30} {'Registrado':<20}")
    print("-" * 80)
    for u in users:
        t = u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "N/A"
        email = u.email or "-"
        print(f"{u.id:<5} {u.name:<25} {email:<30} {t:<20}")


def main():
    init_db()
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    commands = {
        "register": cmd_register,
        "attendance": cmd_attendance,
        "today": cmd_today,
        "users": cmd_users,
    }
    if cmd in commands:
        commands[cmd]()
    else:
        print(f"Comando desconocido: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
