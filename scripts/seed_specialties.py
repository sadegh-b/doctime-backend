# app/schemas/doctor.py

from pydantic import BaseModel, Field
from typing import Optional


class DoctorCreate(BaseModel):
    medical_council_number: str = Field(..., description="شماره نظام پزشکی (اجباری)")
    specialty_id: int = Field(..., description="شناسه عددی تخصص پزشک")
    province: str = Field(..., min_length=2, max_length=120, description="استان مطب")
    city: str = Field(..., min_length=2, max_length=120, description="شهر مطب")
    sub_specialty: Optional[str] = Field(default=None, max_length=120, description="فوق تخصص")
    work_shift: str = Field(default="morning", max_length=20, description="شیفت کاری")
    address: Optional[str] = Field(default=None, max_length=500, description="آدرس دقیق مطب")
    latitude: Optional[float] = Field(default=None, description="عرض جغرافیایی")
    longitude: Optional[float] = Field(default=None, description="طول جغرافیایی")
    bio: Optional[str] = Field(default=None, max_length=2000, description="بیوگرافی")
    experience_years: int = Field(default=0, ge=0, le=80, description="سال‌های تجربه کاری")
    consultation_fee: int = Field(default=0, ge=0, le=10_000_000, description="هزینه ویزیت به ریال")
    waiting_time_estimate: str = Field(default="کمتر از نیم ساعت", max_length=100, description="تخمین زمان انتظار")


class DoctorUpdate(BaseModel):
    specialty_id: Optional[int] = Field(default=None, description="شناسه عددی تخصص پزشک")
    province: Optional[str] = Field(default=None, min_length=2, max_length=120)
    city: Optional[str] = Field(default=None, min_length=2, max_length=120)
    sub_specialty: Optional[str] = Field(default=None, max_length=120)
    work_shift: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    bio: Optional[str] = Field(default=None, max_length=2000)
    experience_years: Optional[int] = Field(default=None, ge=0, le=80)
    consultation_fee: Optional[int] = Field(default=None, ge=0, le=10_000_000)
    waiting_time_estimate: Optional[str] = Field(default=None, max_length=100)


class DoctorResponse(BaseModel):
    id: int
    user_id: int
    specialty_id: int
    specialty_name: Optional[str] = None
    medical_council_number: str
    sub_specialty: Optional[str] = None
    work_shift: str
    province: str
    city: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bio: Optional[str] = None
    experience_years: int = 0
    consultation_fee: int = 0
    waiting_time_estimate: str

    # متد دریافت داده‌ها از دیتابیس و نگاشت به Pydantic با رعایت ارتباطات (Relationships)
    @classmethod
    def model_validate(cls, obj, **kwargs):
        specialty_name = obj.specialty_relation.name if getattr(obj, "specialty_relation", None) else None
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            specialty_id=obj.specialty_id,
            specialty_name=specialty_name,
            medical_council_number=obj.medical_council_number,
            sub_specialty=obj.sub_specialty,
            work_shift=obj.work_shift,
            province=obj.province,
            city=obj.city,
            address=obj.address,
            latitude=obj.latitude,
            longitude=obj.longitude,
            bio=obj.bio,
            experience_years=obj.experience_years,
            consultation_fee=obj.consultation_fee,
            waiting_time_estimate=obj.waiting_time_estimate,
        )

    model_config = {
        "from_attributes": True,
    }


class DoctorProfileResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    role: str
    specialty_id: Optional[int] = None
    specialty_name: Optional[str] = None
    medical_council_number: Optional[str] = None
    sub_specialty: Optional[str] = None
    work_shift: str
    province: str
    city: str
    address: Optional[str] = None
    bio: Optional[str] = None
    experience_years: int = 0
    consultation_fee: int = 0
    waiting_time_estimate: str


class DoctorListItem(BaseModel):
    id: int
    user_id: int
    name: Optional[str] = None
    specialty_id: Optional[int] = None
    specialty_name: Optional[str] = None
    work_shift: str
    city: str
    address: Optional[str] = None
    bio: Optional[str] = None
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
