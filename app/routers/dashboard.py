from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Candidate, Company, Interview, User
from app.routers.auth import get_current_user

router = APIRouter()


@router.get("/dashboard/summary")
async def dashboard_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = db.query(Company).first()
    jobs = 3
    candidates = db.query(Candidate).count()
    interviews = db.query(Interview).count()
    return {
        "user": current_user.email,
        "company": company.name if company else "Acme Labs",
        "jobs": jobs,
        "candidates": candidates,
        "interviews": interviews,
        "company_count": db.query(Company).count(),
    }
