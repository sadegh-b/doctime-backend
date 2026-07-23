# Path: backend/app/schemas/doctor.py

from pydantic import BaseModel, Field


class DoctorCreate(BaseModel):
    specialty_id: int = Field(..., description="شناسه عددی تخصص پزشک")
    city: str = Field(min_length=2, max_length=120)
    work_shift: str = Field(default="morning", max_length=20)
    address: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=1000)
    experience_years: int = Field(default=0, ge=0, le=80)
    consultation_fee: int = Field(default=0, ge=0, le=1_000_000)


class DoctorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    specialty_id: int | None = Field(default=None, description="شناسه عددی تخصص پزشک")
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
    specialty_id: int
    # اصلاح شد: فیلد specialty_name به صورت اختیاری برای نگاشت ویژگی در مدل قرار گرفت
    specialty_name: str | None = None
    work_shift: str
    city: str
    address: str | None = None
    bio: str | None = None
    experience_years: int = 0
    consultation_fee: int = 0

    # متد دریافت داده‌ها از دیتابیس و نگاشت به Pydantic
    @classmethod
    def model_validate(cls, obj, **kwargs):
        specialty_name = obj.specialty_relation.name if getattr(obj, "specialty_relation", None) else None
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            specialty_id=obj.specialty_id,
            specialty_name=specialty_name,
            work_shift=obj.work_shift,
            city=obj.city,
            address=obj.address,
            bio=obj.bio,
            experience_years=obj.experience_years,
            consultation_fee=obj.consultation_fee,
        )

    model_config = {
        "from_attributes": True,
    }


class DoctorProfileResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: str | None = None
    role: str
    specialty_id: int | None = None
    specialty_name: str | None = None
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
    specialty_id: int | None = None
    specialty_name: str | None = None
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
