from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import InterviewInvitation
from app.routers.auth import get_current_user
from app.services.assemblyai import generate_assemblyai_token

router = APIRouter()


@router.post("/session-token")
async def get_assemblyai_session_token(current_user=Depends(get_current_user)):
    return {"token": await generate_assemblyai_token(), "expires_in": 600}


@router.post("/session-token/{token}")
async def get_candidate_assemblyai_session_token(token: str, db: Session = Depends(get_db)):
    invitation = db.query(InterviewInvitation).filter(InterviewInvitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return {"token": await generate_assemblyai_token(), "expires_in": 600}
