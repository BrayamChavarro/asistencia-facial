from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse
import os

router = APIRouter(tags=["pages"])
BASE = os.path.dirname(os.path.dirname(__file__))


@router.get("/", response_class=HTMLResponse)
def user_view():
    return FileResponse(os.path.join(BASE, "templates", "user.html"))


@router.get("/admin", response_class=HTMLResponse)
def admin_view():
    return FileResponse(os.path.join(BASE, "templates", "admin.html"))
