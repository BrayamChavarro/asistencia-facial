import sys
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.routers import users, attendance, pages, face, dashboard
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Asistencia Facial", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "uploads")), name="uploads")
app.include_router(pages.router)
app.include_router(users.router)
app.include_router(attendance.router)
app.include_router(face.router)
app.include_router(dashboard.router)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "http"
    opts = {"host": "0.0.0.0", "reload": False}
    if mode == "https":
        uvicorn.run("main:app", port=8443, ssl_keyfile="key.pem", ssl_certfile="cert.pem", **opts)
    else:
        uvicorn.run("main:app", port=8000, **opts)
