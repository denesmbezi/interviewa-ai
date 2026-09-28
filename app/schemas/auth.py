from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegistrationRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str | None = None
