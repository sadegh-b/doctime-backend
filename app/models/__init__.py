from app.database.base import Base
from app.database.session import engine

from app.models.user import User
from app.models.doctor import Doctor
from app.models.availability import Availability
from app.models.appointment import Appointment

Base.metadata.create_all(bind=engine)
