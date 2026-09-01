import uuid
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from .api import audio, auth, curriculum, devices, learning, practice, reading, students, textbooks, tutor
from .config import get_settings
from .database import Base, SessionLocal, engine
from .models import Subject

settings = get_settings()
logger = logging.getLogger(__name__)
app = FastAPI(title="AI Primary Tutor API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request error", extra={"request_id": request_id})
        response = JSONResponse(status_code=500, content={"code": "internal_error", "message": "Unexpected server error", "request_id": request_id})
    response.headers["X-Request-ID"] = request_id
    return response


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for code, name, enabled in [("english", "英语", True), ("chinese", "语文", False), ("math", "数学", False)]:
            if not db.scalar(select(Subject).where(Subject.code == code)):
                db.add(Subject(code=code, name=name, enabled=enabled))
        db.commit()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}


for router in [auth.router, students.router, tutor.router, audio.router, curriculum.router, practice.router, reading.router, textbooks.router, learning.router, devices.router]:
    app.include_router(router, prefix="/api/v1")
