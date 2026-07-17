from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models

from app.api.routes.auth import router as auth_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.availability import router as availability_router
from app.api.routes.reviews import router as reviews_router


app = FastAPI(
    title="DocTime API",
    description="Doctor Appointment Management System",
    version="1.0.0",
)


allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://doctime-frontend-omega.vercel.app",
]


extra_origin = getenv("FRONTEND_URL")

if extra_origin:
    allowed_origins.append(extra_origin)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.options("/{path:path}")
async def options_handler(path: str):
    return {"message": "OK"}


@app.get("/")
def root():
    return {
        "status": "online",
        "allowed_origins": allowed_origins,
    }


app.include_router(auth_router, prefix="/api/v1")
app.include_router(doctors_router, prefix="/api/v1")
app.include_router(appointments_router, prefix="/api/v1")
app.include_router(availability_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")