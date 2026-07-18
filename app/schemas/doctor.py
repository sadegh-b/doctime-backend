from pydantic import BaseModel, Field


class DoctorCreate(BaseModel):
    specialty: str
    city: str
    work_shift: str | None = None
    address: str | None = None
    bio: str | None = None
    experience_years: int = Field(default=0, ge=0, le=80)
    consultation_fee: int = Field(default=0, ge=0, le=1_000_000)


class DoctorResponse(BaseModel):
    id: int
    user_id: int
    specialty: str
    work_shift: str | None = None
    city: str
    address: str | None = None
    bio: str | None = None
    experience_years: int = 0
    consultation_fee: int = 0

    model_config = {"from_attributes": True}


class DoctorListItem(BaseModel):
    id: int
    user_id: int
    name: str | None = None
    specialty: str
    work_shift: str | None = None
    city: str
    address: str | None = None
    bio: str | None = None
    experience_years: int = 0
    consultation_fee: int = 0


class DoctorListResponse(BaseModel):
    success: bool
    count: int
    items: list[DoctorListItem]


class DoctorCreateResponse(BaseModel):
    success: bool
    data: DoctorResponse
