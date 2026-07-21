from typing import Optional, Union

from pydantic import BaseModel, ConfigDict

from app.schemas.user import DoctorOut, UserOut


class UserLogin(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    message: str
    user: Union[DoctorOut, UserOut]
    token: Optional[TokenResponse] = None

    model_config = ConfigDict(from_attributes=True)


AuthResponse = UserResponse
