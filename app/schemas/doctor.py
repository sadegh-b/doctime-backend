from pydantic import BaseModel, Field


class DoctorCreate(BaseModel):
    specialty: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=120)
    work_shift: str = Field(default="morning", max_length=20)
    address: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=1000)
    experience_years: int = Field(default=0, ge=0, le=80)
    consultation_fee: int = Field(default=0, ge=0, le=1_000_000)


class DoctorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    specialty: str | None = Field(default=None, min_length=2, max_length=120)
    city: str | None = Field(default=None, min_length=2, max_length=120)
    work_shift: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=1000)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    consultation_fee: int | None = Field(
        default=None,
        ge=0,
        le=1_000_000,
    )


class DoctorResponse(BaseModel):
    id: int
    user_id: int
    specialty: str
    work_shift: str
    city: str
    address: str | None = None
    bio: str | None = None
    experience_years: int = 0
    consultation_fee: int = 0

    model_config = {
        "from_attributes": True,
    }


class DoctorProfileResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: str | None = None
    role: str
    specialty: str
    work_shift: str
    city: str
    address: str | None = None
    bio: str | None = None
    experience_years: int = 0
    consultation_fee: int = 0


class DoctorListItem(BaseModel):
    id: int
    user_id: int
    name: str | None = None
    specialty: str
    work_shift: str
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


class DoctorProfileApiResponse(BaseModel):
    success: bool
    data: DoctorProfileResponse
