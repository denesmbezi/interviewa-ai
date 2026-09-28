from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models import Company, CompanyMembership, User
from app.schemas.auth import LoginRequest, RegistrationRequest

settings = get_settings()
security = HTTPBearer(auto_error=False)
auth_router = APIRouter()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    auth: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if token is None and auth is not None:
        token = auth.credentials
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = decode_access_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@auth_router.post("/login")
async def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.email)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.access_token_expire_minutes * 60,
    )
    return {"message": "Logged in", "user": {"id": user.id, "email": user.email, "full_name": user.full_name}}


@auth_router.post("/register/candidate")
async def register_candidate(payload: RegistrationRequest, response: Response, db: Session = Depends(get_db)):
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(email=payload.email, full_name=payload.full_name, password_hash=get_password_hash(payload.password), is_verified=True)
    db.add(user)
    db.commit()
    token = create_access_token(user.email)
    response.set_cookie(key=settings.session_cookie_name, value=token, httponly=True, samesite="lax", secure=False, max_age=settings.access_token_expire_minutes * 60)
    return {"message": "Candidate account created", "user": {"id": user.id, "email": user.email, "full_name": user.full_name}}


@auth_router.post("/register/company")
async def register_company(payload: RegistrationRequest, response: Response, db: Session = Depends(get_db)):
    if not payload.company_name:
        raise HTTPException(status_code=400, detail="company_name is required")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email is already registered")
    company = Company(name=payload.company_name)
    user = User(email=payload.email, full_name=payload.full_name, password_hash=get_password_hash(payload.password), is_verified=True)
    db.add_all([company, user])
    db.flush()
    db.add(CompanyMembership(company_id=company.id, user_id=user.id, role="Hiring Team"))
    db.commit()
    token = create_access_token(user.email)
    response.set_cookie(key=settings.session_cookie_name, value=token, httponly=True, samesite="lax", secure=False, max_age=settings.access_token_expire_minutes * 60)
    return {"message": "Company account created", "company_id": company.id, "user": {"id": user.id, "email": user.email, "full_name": user.full_name}}


@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=settings.session_cookie_name)
    return {"message": "Logged out"}


@auth_router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    company_membership = current_user.memberships[0] if current_user.memberships else None
    raw_role = company_membership.role if company_membership else "Candidate"
    role = "Candidate" if raw_role == "Candidate" else "Hiring Team"
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": role,
    }
