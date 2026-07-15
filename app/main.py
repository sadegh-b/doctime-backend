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

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "message": "DocTime API is running successfully",
    }


app.include_router(auth_router, prefix="/api/v1")
app.include_router(doctors_router, prefix="/api/v1")
app.include_router(appointments_router, prefix="/api/v1")
app.include_router(availability_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
