import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=True)
    embedding = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    active = Column(Integer, default=1)

    attendances = relationship("Attendance", back_populates="user", cascade="all, delete-orphan")


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    confidence = Column(Float, nullable=True)
    image_path = Column(String(255), nullable=True)
    type = Column(String(10), nullable=True, default=None)

    user = relationship("User", back_populates="attendances")


Index("idx_attendance_user_date", Attendance.user_id, Attendance.timestamp)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    return db
