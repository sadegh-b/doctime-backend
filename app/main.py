# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.availability import router as availability_router

app = FastAPI(
    title="DocTime API",
    description="Doctor Appointment Management System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# مسیر ریشه برای تست سلامت سیستم
@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "message": "DocTime API is running successfully"
    }

# اضافه کردن روترها با سازماندهی بهتر
app.include_router(auth_router, prefix="/api/v1")
app.include_router(doctors_router, prefix="/api/v1")
app.include_router(appointments_router, prefix="/api/v1")
app.include_router(availability_router, prefix="/api/v1")
