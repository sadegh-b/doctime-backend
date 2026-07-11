# app/schemas/doctor.py
from pydantic import BaseModel, Field


class DoctorCreate(BaseModel):
    specialty: str
    city: str
    address: str | None = None
    bio: str | None = None
    experience_years: int = Field(ge=0, le=80)
    consultation_fee: int = Field(ge=0, le=1_000_000)

    # English tip:
    # experience_years تلفظ: اِکسپیریِنس ییرز
    # consultation_fee تلفظ: کانسالتِیشِن فی (هزینه ویزیت)


class DoctorResponse(BaseModel):
    id: int
    user_id: int
    specialty: str
    city: str
    address: str | None = None
    bio: str | None = None
    experience_years: int
    consultation_fee: int

    model_config = {"from_attributes": True}


class DoctorListItem(BaseModel):
    id: int
    user_id: int
    name: str | None = None
    specialty: str
    city: str
    address: str | None = None
    bio: str | None = None
    experience_years: int
    consultation_fee: int


class DoctorListResponse(BaseModel):
    success: bool
    count: int
    items: list[DoctorListItem]


class DoctorCreateResponse(BaseModel):
    success: bool
    data: DoctorResponse
