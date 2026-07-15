from app.database.base import Base
from app.database.session import engine

from app.models.user import User

Base.metadata.create_all(bind=engine)
