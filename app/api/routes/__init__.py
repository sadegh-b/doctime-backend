# app/api/routes/__init__.py

from . import auth
from . import doctors
from . import availability
from . import appointments
from . import reviews

__all__ = [
    "auth",
    "doctors",
    "availability",
    "appointments",
    "reviews",
]