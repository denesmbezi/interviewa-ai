from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import json

from app.db.session import get_db
from app.models import Candidate, Company, Interview, InterviewInvitation, User
from app.routers.auth import get_current_user

router = APIRouter()


@router.get("/recruiter/company")
async def recruiter_company(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = db.query(Company).first()
    if not company:
        return {"name": "Acme Labs", "id": 1}
    return {"id": company.id, "name": company.name}


@router.get("/recruiter/interviews")
async def recruiter_interviews(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    base_url = str(request.base_url).rstrip("/")
    interviews = db.query(Interview).all()
    rows = []
    for interview in interviews:
        candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
        invitation = db.query(InterviewInvitation).filter(InterviewInvitation.interview_id == interview.id).first()
        rows.append(
            {
                "id": interview.id,
                "status": interview.status,
                "candidate_name": candidate.full_name if candidate else "Unknown",
                "candidate_email": candidate.email if candidate else "",
                "job_id": interview.job_id,
                "consent_status": interview.consent_status,
                "share_url": f"{base_url}/candidate/interview/{invitation.token}" if invitation else "",
            }
        )
    return rows


@router.post("/recruiter/invite-candidate")
async def recruit_invite_candidate(payload: dict, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company_id = payload.get("company_id")
    candidate_name = payload.get("candidate_name")
    candidate_email = payload.get("candidate_email")
    if not company_id or not candidate_name or not candidate_email:
        raise HTTPException(status_code=400, detail="company_id, candidate_name and candidate_email are required")

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    candidate = Candidate(company_id=company_id, full_name=candidate_name, email=candidate_email)
    db.add(candidate)
    db.flush()

    interview = Interview(
        company_id=company_id,
        job_id=payload.get("job_id", 1),
        candidate_id=candidate.id,
        interviewer_id=current_user.id,
        status="scheduled",
        consent_status="pending",
    )
    db.add(interview)
    db.flush()

    token = payload.get("token") or __import__("uuid").uuid4().hex
    invitation = InterviewInvitation(
        company_id=company_id,
        interview_id=interview.id,
        token=token,
        expires_at=__import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(days=1),
    )
    db.add(invitation)
    db.commit()

    base_url = str(request.base_url).rstrip("/")
    return {
        "message": "Invitation created",
        "share_url": f"{base_url}/candidate/interview/{token}",
        "interview_id": interview.id,
    }


# Interviewer Training Simulator - Recruiter practices with AI candidate
TRAINING_PERSONAS = {
    "nervous_junior": {
        "name": "Alex (Nervous Junior)",
        "description": "Recent graduate, anxious, gives brief answers, needs encouragement",
        "system_prompt": "You are Alex, a nervous recent graduate interviewing for a junior role. You speak softly, give brief answers, sometimes freeze up. You're eager but lack confidence. You use filler words ('um', 'uh'). You need gentle encouragement.",
        "voice": "anna",
    },
    "experienced_leader": {
        "name": "Maria (Experienced Leader)",
        "description": "Senior professional, confident, detailed answers, challenges assumptions",
        "system_prompt": "You are Maria, a senior professional with 15 years experience. You're confident, articulate, and give detailed STAR-method answers. You sometimes challenge the interviewer's premises. You ask clarifying questions back.",
        "voice": "anna",
    },
    "career_changer": {
        "name": "James (Career Changer)",
        "description": "Mid-career switcher, translates transferable skills, addresses gaps honestly",
        "system_prompt": "You are James, switching from marketing to product management. You're good at translating transferable skills but have genuine knowledge gaps. You're honest about what you don't know but show how you'd learn it. You give concrete examples from past roles.",
        "voice": "anna",
    },
    "overconfident": {
        "name": "Sam (Overconfident)",
        "description": "Talks a lot, exaggerates achievements, dismisses feedback, needs redirecting",
        "system_prompt": "You are Sam, an overconfident candidate who talks extensively, exaggerates your role in past successes, and dismisses follow-up questions. You need firm but polite redirection. You rarely ask questions yourself.",
        "voice": "anna",
    },
    "non_native_english": {
        "name": "Priya (Non-Native English Speaker)",
        "description": "Strong candidate with accent, occasional grammar issues, precise technical knowledge",
        "system_prompt": "You are Priya, a strong technical candidate with a noticeable accent and occasional grammar issues. Your content is excellent but delivery isn't perfect. You pause to find words. You should NOT be penalized for accent or fluency - focus on substance.",
        "voice": "anna",
    },
}


@router.get("/recruiter/training/personas")
async def get_training_personas():
    return {key: {"name": v["name"], "description": v["description"]} for key, v in TRAINING_PERSONAS.items()}


@router.get("/recruiter/training/{persona_key}", response_class=HTMLResponse)
async def training_interview_page(persona_key: str, request: Request, db: Session = Depends(get_db)):
    if persona_key not in TRAINING_PERSONAS:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    persona = TRAINING_PERSONAS[persona_key]
    company = db.query(Company).first()
    
    with open("app/templates/training_interview.html", "r", encoding="utf-8") as f:
        content = f.read()
        content = content.replace("{{PERSONA_NAME}}", persona["name"])
        content = content.replace("{{PERSONA_DESCRIPTION}}", persona["description"])
        content = content.replace("{{PERSONA_SYSTEM_PROMPT}}", json.dumps(persona["system_prompt"])[1:-1])
        content = content.replace("{{PERSONA_VOICE}}", persona["voice"])
        content = content.replace("{{COMPANY_NAME}}", company.name if company else "Interviewa AI")
        return HTMLResponse(content=content)
