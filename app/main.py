from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models
from app.api.routes.appointments import router as appointments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.availability import router as availability_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.reviews import router as reviews_router


app = FastAPI(
    title="DocTime API",
    description="Doctor Appointment Management System",
    version="1.0.0",
)


def build_allowed_origins() -> list[str]:
    origins = {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://doctime-frontend-omega.vercel.app",
    }

    frontend_url = getenv("FRONTEND_URL", "").strip()

    if frontend_url:
        origins.add(frontend_url.rstrip("/"))

    extra_origins = getenv("ALLOWED_ORIGINS", "").strip()

    if extra_origins:
        for origin in extra_origins.split(","):
            cleaned = origin.strip().rstrip("/")
            if cleaned:
                origins.add(cleaned)

    return list(origins)


allowed_origins = build_allowed_origins()


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "message": "DocTime API is running successfully",
        "allowed_origins": allowed_origins,
    }


app.include_router(
    auth_router,
    prefix="/api/v1",
)

app.include_router(
    doctors_router,
    prefix="/api/v1",
)

app.include_router(
    appointments_router,
    prefix="/api/v1",
)

app.include_router(
    availability_router,
    prefix="/api/v1",
)

app.include_router(
    reviews_router,
    prefix="/api/v1",
)