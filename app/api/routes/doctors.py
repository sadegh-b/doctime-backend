# Path: backend/app/api/routes/doctors.py

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user, get_db
from app.models.doctor import Doctor, Specialty
from app.models.user import User


router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"],
)


# ==========================================
# Pydantic Schemas
# ==========================================

class SpecialtyResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }


class UserBriefResponse(BaseModel):
    id: int
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    phone_number: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }


class DoctorResponse(BaseModel):
    id: int
    user_id: int

    medical_council_number: Optional[str] = None
    specialty_id: Optional[int] = None
    sub_specialty: Optional[str] = None

    work_shift: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None

    experience_years: int = 0
    consultation_fee: int = 0

    user: UserBriefResponse

    specialty: Optional[SpecialtyResponse] = Field(
        default=None,
        validation_alias="specialty_relation",
    )

    model_config = {
        "from_attributes": True,
    }


class DoctorRegisterRequest(BaseModel):
    medical_council_number: str
    specialty_id: int
    province: str
    city: str
    work_shift: str = "morning"
    experience_years: int = 0
    consultation_fee: int = 0


class DoctorUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

    specialty_id: Optional[int] = None

    province: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None

    work_shift: Optional[str] = None
    experience_years: Optional[int] = None
    consultation_fee: Optional[int] = None


# ==========================================
# Helper Functions
# ==========================================

def normalize_persian_text(value: str) -> str:
    """
    نرمال‌سازی اولیه متن فارسی در سطح Python.

    ي -> ی
    ك -> ک
    حذف فاصله‌های ابتدا و انتهای رشته
    تبدیل چند فاصله متوالی به یک فاصله
    """
    normalized_value = (
        value
        .replace("ي", "ی")
        .replace("ى", "ی")
        .replace("ك", "ک")
        .strip()
    )

    return " ".join(normalized_value.split())


def normalize_persian_sql_column(column: Any) -> Any:
    """
    نرمال‌سازی حروف عربی داخل ستون دیتابیس در سطح SQL.
    سازگار با SQLite و PostgreSQL.

    مهم: جایگزینی‌ها باید تو-در-تو (nested) باشند، چون نمی‌توان
    یک expression SQL را در Python با خروجی تابع بعدی overwrite کرد.

    coalesce باعث می‌شود اگر مقدار ستون NULL بود، خطا ندهد و
    به رشته خالی تبدیل شود.
    """
    col = func.coalesce(column, "")

    return func.replace(
        func.replace(
            func.replace(
                col,
                "ي",
                "ی",
            ),
            "ى",
            "ی",
        ),
        "ك",
        "ک",
    )


def validate_optional_text(
    value: Optional[str],
    field_label: str,
) -> Optional[str]:
    """
    رشته‌های اختیاری را trim می‌کند.

    اگر کاربر فقط فاصله ارسال کرده باشد، مقدار None برمی‌گرداند.
    """
    if value is None:
        return None

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    if len(cleaned_value) > 5000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_label} بیش از حد طولانی است.",
        )

    return cleaned_value


# ==========================================
# Endpoints
# ==========================================

@router.get(
    "/",
    response_model=List[DoctorResponse],
)
def get_doctors_list(
    specialty_slug: Optional[str] = Query(
        default=None,
        description="شناسه متنی تخصص مانند cardiology",
    ),
    city: Optional[str] = Query(
        default=None,
        description="فیلتر شهر",
    ),
    search: Optional[str] = Query(
        default=None,
        description="جستجو در نام، نام خانوادگی، نام کامل، بیوگرافی و تخصص",
    ),
    db: Session = Depends(get_db),
) -> Any:
    """
    دریافت لیست پزشکان.

    قابلیت‌ها:
    - فیلتر براساس تخصص
    - فیلتر براساس شهر
    - جستجوی چندکلمه‌ای
    - جستجو در نام، نام خانوادگی، نام کامل، بیوگرافی و تخصص
    - نرمال‌سازی ی و ک عربی/فارسی
    """

    query = (
        db.query(Doctor)
        .join(User)
        .outerjoin(Specialty, Doctor.specialty_id == Specialty.id)
        .options(
            joinedload(Doctor.user),
            joinedload(Doctor.specialty_relation),
        )
    )

    normalized_specialty_slug = (
        specialty_slug.strip()
        if specialty_slug and specialty_slug.strip()
        else None
    )

    if normalized_specialty_slug:
        query = query.filter(
            Specialty.slug == normalized_specialty_slug
        )

    normalized_city = (
        normalize_persian_text(city)
        if city and city.strip()
        else None
    )

    if normalized_city:
        normalized_city_column = normalize_persian_sql_column(
            Doctor.city
        )

        query = query.filter(
            normalized_city_column.ilike(
                f"%{normalized_city}%"
            )
        )

    normalized_search = (
        normalize_persian_text(search)
        if search and search.strip()
        else None
    )

    if normalized_search:
        search_terms = [
            term
            for term in normalized_search.split(" ")
            if term
        ]

        normalized_first_name = normalize_persian_sql_column(
            User.first_name
        )
        normalized_last_name = normalize_persian_sql_column(
            User.last_name
        )
        normalized_user_name = normalize_persian_sql_column(
            User.name
        )
        normalized_bio = normalize_persian_sql_column(
            Doctor.bio
        )
        normalized_specialty_name = normalize_persian_sql_column(
            Specialty.name
        )
        normalized_specialty_slug = normalize_persian_sql_column(
            Specialty.slug
        )

        # SQLite از عملگر + به عنوان || (concat) استفاده می‌کند
        normalized_full_name = func.trim(
            normalized_first_name + " " + normalized_last_name
        )

        # جستجوی کل عبارت کامل
        full_search_pattern = f"%{normalized_search}%"

        query = query.filter(
            or_(
                normalized_first_name.ilike(full_search_pattern),
                normalized_last_name.ilike(full_search_pattern),
                normalized_user_name.ilike(full_search_pattern),
                normalized_full_name.ilike(full_search_pattern),
                normalized_bio.ilike(full_search_pattern),
                normalized_specialty_name.ilike(full_search_pattern),
                normalized_specialty_slug.ilike(full_search_pattern),
            )
        )

        # جستجوی term-by-term
        # هر term باید در حداقل یکی از فیلدها وجود داشته باشد
        for term in search_terms:
            term_pattern = f"%{term}%"

            query = query.filter(
                or_(
                    normalized_first_name.ilike(term_pattern),
                    normalized_last_name.ilike(term_pattern),
                    normalized_user_name.ilike(term_pattern),
                    normalized_full_name.ilike(term_pattern),
                    normalized_bio.ilike(term_pattern),
                    normalized_specialty_name.ilike(term_pattern),
                    normalized_specialty_slug.ilike(term_pattern),
                )
            )

    doctors = (
        query
        .distinct()
        .order_by(Doctor.id.desc())
        .all()
    )

    return doctors


# توجه:
# Route ثابت /me باید قبل از Route داینامیک /{doctor_id} تعریف شود.
#
# در غیر این صورت FastAPI ممکن است "me" را به عنوان doctor_id
# تفسیر کند و خطای 422 ایجاد شود.

@router.put(
    "/me",
    response_model=DoctorResponse,
)
def update_my_doctor_profile(
    payload: DoctorUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    ویرایش پروفایل پزشک واردشده.
    """

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.user_id == current_user.id
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پروفایل پزشک یافت نشد.",
        )

    data = payload.model_dump(
        exclude_unset=True
    )

    if "first_name" in data:
        current_user.first_name = validate_optional_text(
            data.pop("first_name"),
            "نام",
        )

    if "last_name" in data:
        current_user.last_name = validate_optional_text(
            data.pop("last_name"),
            "نام خانوادگی",
        )

    if "phone" in data:
        normalized_phone = validate_optional_text(
            data.pop("phone"),
            "شماره تلفن",
        )

        if normalized_phone is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="شماره تلفن نمی‌تواند خالی باشد.",
            )

        current_user.phone = normalized_phone

    current_user.name = " ".join(
        part
        for part in [
            current_user.first_name,
            current_user.last_name,
        ]
        if part and part.strip()
    ).strip()

    if "specialty_id" in data:
        specialty_id = data.pop("specialty_id")

        if specialty_id is None or specialty_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="شناسه تخصص معتبر نیست.",
            )

        specialty_exists = (
            db.query(Specialty.id)
            .filter(
                Specialty.id == specialty_id
            )
            .first()
        )

        if not specialty_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="تخصص انتخاب‌شده یافت نشد.",
            )

        doctor.specialty_id = specialty_id

    if "province" in data:
        doctor.province = validate_optional_text(
            data.pop("province"),
            "استان",
        )

    if "city" in data:
        doctor.city = validate_optional_text(
            data.pop("city"),
            "شهر",
        )

    if "address" in data:
        doctor.address = validate_optional_text(
            data.pop("address"),
            "آدرس",
        )

    if "bio" in data:
        doctor.bio = validate_optional_text(
            data.pop("bio"),
            "توضیحات",
        )

    if "work_shift" in data:
        doctor.work_shift = validate_optional_text(
            data.pop("work_shift"),
            "شیفت کاری",
        )

    if "experience_years" in data:
        experience_years = data.pop(
            "experience_years"
        )

        if experience_years is None or experience_years < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="سابقه کاری نمی‌تواند منفی باشد.",
            )

        doctor.experience_years = experience_years

    if "consultation_fee" in data:
        consultation_fee = data.pop(
            "consultation_fee"
        )

        if consultation_fee is None or consultation_fee < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="هزینه ویزیت نمی‌تواند منفی باشد.",
            )

        doctor.consultation_fee = consultation_fee

    if data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "فیلدهای ناشناخته برای ویرایش پروفایل وجود دارد.",
                "fields": list(data.keys()),
            },
        )

    try:
        db.add(current_user)
        db.add(doctor)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ذخیره تغییرات پروفایل با خطا مواجه شد.",
        )

    updated_doctor = (
        db.query(Doctor)
        .options(
            joinedload(Doctor.user),
            joinedload(Doctor.specialty_relation),
        )
        .filter(
            Doctor.id == doctor.id
        )
        .first()
    )

    if not updated_doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پروفایل پزشک پس از ویرایش یافت نشد.",
        )

    return updated_doctor


@router.get(
    "/{doctor_id}",
    response_model=DoctorResponse,
)
def get_doctor_profile(
    doctor_id: int = Path(
        ...,
        gt=0,
        description="شناسه عددی پزشک",
    ),
    db: Session = Depends(get_db),
) -> Any:
    """
    دریافت اطلاعات یک پزشک براساس شناسه پزشک.
    """

    doctor = (
        db.query(Doctor)
        .options(
            joinedload(Doctor.user),
            joinedload(Doctor.specialty_relation),
        )
        .filter(
            Doctor.id == doctor_id
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="پزشک یافت نشد.",
        )

    return doctor
