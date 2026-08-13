from app.database.session import SessionLocal
from app.models.doctor import Doctor
from app.models.user import User


def fix_doctor_profile(user_id: int = 5) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            print(f"User with id={user_id} not found")
            return

        print(f"Found user: id={user.id}, email={user.email}, role={user.role}")

        if user.role != "doctor":
            user.role = "doctor"
            print("Updated user role to doctor")

        doctor = db.query(Doctor).filter(Doctor.user_id == user_id).first()
        if doctor is not None:
            print(
                f"Doctor profile already exists: doctor_id={doctor.id}, user_id={doctor.user_id}"
            )
            db.commit()
            return

        doctor = Doctor(
            user_id=user_id,
            specialty="General Medicine",
            city="Zahedan",
            address="Temporary address - update later",
            bio="Created by fix script",
            experience_years=0,
            consultation_fee=0,
        )

        db.add(doctor)
        db.commit()
        db.refresh(doctor)

        print(
            f"Doctor profile created successfully: doctor_id={doctor.id}, user_id={doctor.user_id}"
        )
    except Exception as exc:
        db.rollback()
        print(f"Fix failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_doctor_profile()
