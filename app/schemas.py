import datetime
from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    name: str
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    created_at: datetime.datetime
    active: int

    class Config:
        from_attributes = True


class AttendanceResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    timestamp: datetime.datetime
    confidence: Optional[float] = None
    type: Optional[str] = None
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True


class RecognitionResult(BaseModel):
    success: bool
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    confidence: Optional[float] = None
    message: str
    type: Optional[str] = None
    photo_url: Optional[str] = None


class RegisterResult(BaseModel):
    success: bool
    user_id: Optional[int] = None
    message: str


class UserDetailResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    created_at: datetime.datetime
    active: int
    total_attendances: int
    today_attendances: list[AttendanceResponse]
    recent_attendances: list[AttendanceResponse]

    class Config:
        from_attributes = True


class UserPhotosResponse(BaseModel):
    date: str
    entry: Optional[str] = None
    exit: Optional[str] = None
    entry_confidence: Optional[float] = None
    exit_confidence: Optional[float] = None
