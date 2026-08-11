import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.patients import router as patients_router
from app.api.voice import router as voice_router
from app.config import get_settings
from app.database import Base, engine
from app.services.patients import EmptyUpdateError, PatientNotFoundError

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("patient-registration")


@asynccontextmanager
async def lifespan(application: FastAPI):
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
if settings.origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Idempotency-Key", "X-Vapi-Secret"],
    )

app.include_router(patients_router)
app.include_router(voice_router)


def error(status: int, code: str, message: str, request_id: str, details=None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"data": None, "error": {"code": code, "message": message, "details": details, "request_id": request_id}},
    )


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(part) for part in item["loc"] if part != "body"), "message": item["msg"]}
        for item in exc.errors()
    ]
    return error(422, "VALIDATION_ERROR", "One or more fields are invalid.", request.state.request_id, details)


@app.exception_handler(PatientNotFoundError)
async def not_found(request: Request, exc: PatientNotFoundError):
    return error(404, "PATIENT_NOT_FOUND", "Patient was not found.", request.state.request_id)


@app.exception_handler(EmptyUpdateError)
async def empty_update(request: Request, exc: EmptyUpdateError):
    return error(400, "EMPTY_UPDATE", "At least one field must be supplied.", request.state.request_id)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    logger.exception("database_error request_id=%s", request.state.request_id)
    return error(500, "DATABASE_ERROR", "The record could not be saved. Please try again.", request.state.request_id)


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"data": {"status": "ok", "database": "connected"}, "error": None}


@app.get("/", include_in_schema=False)
def root():
    return {
        "data": {
            "service": settings.app_name,
            "status": "online",
            "documentation": "/docs",
            "health": "/health",
            "patients": "/patients",
            "notice": "Technical assessment demo. Use fictional patient information only.",
        },
        "error": None,
    }
