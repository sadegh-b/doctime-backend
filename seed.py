# filepath: seed.py
import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.doctor import Doctor
from app.models.availability import Availability
from app.core.security import hash_password

def seed_db():
    db: Session = SessionLocal()
    print("⏳ Starting database seeding...")

    try:
        patient_user = db.query(User).filter(User.email == "patient@doctime.com").first()
        if not patient_user:
            patient_user = User(
                email="patient@doctime.com",
                name="Sadegh Baloch",
                first_name="Sadegh",
                last_name="Baloch",
                phone="09120000001",
                hashed_password=hash_password("password123"),
                role="patient",
                is_active=True
            )
            db.add(patient_user)
            db.flush()
            print("✅ Patient 1 user created.")
        else:
            print("ℹ️ Patient 1 user already exists.")

        patient_user_2 = db.query(User).filter(User.email == "patient2@doctime.com").first()
        if not patient_user_2:
            patient_user_2 = User(
                email="patient2@doctime.com",
                name="Iman Baluchi",
                first_name="Iman",
                last_name="Baluchi",
                phone="09120000003",
                hashed_password=hash_password("password123"),
                role="patient",
                is_active=True
            )
            db.add(patient_user_2)
            db.flush()
            print("✅ Patient 2 user created for concurrency tests.")
        else:
            print("ℹ️ Patient 2 user already exists.")

        doctor_user = db.query(User).filter(User.email == "doctor@doctime.com").first()
        if not doctor_user:
            doctor_user = User(
                email="doctor@doctime.com",
                name="Dr. Ali Rezaei",
                first_name="Ali",
                last_name="Rezaei",
                phone="09120000002",
                hashed_password=hash_password("password123"),
                role="doctor",
                is_active=True
            )
            db.add(doctor_user)
            db.flush()
            print("✅ Doctor user created.")
        else:
            print("ℹ️ Doctor user already exists.")

        doctor_profile = db.query(Doctor).filter(Doctor.user_id == doctor_user.id).first() if doctor_user else None
        if doctor_user and not doctor_profile:
            doctor_profile = Doctor(
                user_id=doctor_user.id,
                city="Tehran",
                address="Vanak Square, No 10",
                bio="Experienced cardiologist specializing in heart failure.",
                experience_years=10,
                consultation_fee=150000
            )
            db.add(doctor_profile)
            db.flush()
            print("✅ Doctor profile created.")
        elif doctor_profile:
            print("ℹ️ Doctor profile already exists.")

        if doctor_profile:
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)
            day_after = today + datetime.timedelta(days=2)

            slots_to_create = [
                {"date": tomorrow, "start_time": datetime.time(9, 0), "end_time": datetime.time(9, 30)},
                {"date": tomorrow, "start_time": datetime.time(10, 0), "end_time": datetime.time(10, 30)},
                {"date": tomorrow, "start_time": datetime.time(11, 0), "end_time": datetime.time(11, 30)},
                {"date": day_after, "start_time": datetime.time(14, 0), "end_time": datetime.time(14, 30)},
                {"date": day_after, "start_time": datetime.time(15, 0), "end_time": datetime.time(15, 30)},
            ]

            for slot_data in slots_to_create:
                existing_slot = db.query(Availability).filter(
                    Availability.doctor_id == doctor_profile.id,
                    Availability.date == slot_data["date"],
                    Availability.start_time == slot_data["start_time"]
                ).first()

                if not existing_slot:
                    new_slot = Availability(
                        doctor_id=doctor_profile.id,
                        date=slot_data["date"],
                        start_time=slot_data["start_time"],
                        end_time=slot_data["end_time"],
                        is_available=True,
                        is_booked=False
                    )
                    db.add(new_slot)

            print("✅ Availability slots generated.")

        db.commit()
        print("🎉 Database seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
