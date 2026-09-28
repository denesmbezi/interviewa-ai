from datetime import datetime, timedelta
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Candidate, Company, ConsentRecord, Interview, InterviewInvitation, Job, JobVersion

router = APIRouter()

INTERVIEW_AREAS = {
    "Earn Customer Loyalty": [
        "Tell me about a time you've exceeded a customer or stakeholder's expectations.",
        "Tell me about a time you have dealt with a particularly challenging customer or stakeholder.",
        "Tell me about a time you did your best to solve a customer or stakeholder issue and the individual was not satisfied.",
        "Can you tell me about a time when you worked with your team to improve customer loyalty?",
    ],
    "Create the Future": [
        "Give me an example of a problem you have solved in a unique way.",
        "Tell me about a time using an established approach did not work for you when solving a business challenge.",
        "Tell me about a time you had to generate many new ideas quickly, individually or as part of a team.",
        "Give me an example of an opportunity that you identified and were able to take advantage of.",
        "Tell me about a time when you created a safe space for others to share ideas.",
    ],
    "Experiment, Learn Fast": [
        "Tell me about a time you changed your approach to work based on feedback.",
        "Give me an example of something you had to change about your approach to work while adapting to virtual or hybrid working practices.",
        "Give me an example of when you helped someone else develop or learn something new.",
    ],
    "Get it Done, Together": [
        "Give me a recent example of when you developed your internal or external network.",
        "Can you think of an example of a time that you enabled or supported a colleague to move their idea forward?",
        "Tell me about a time when you found a team or individual challenging to work with. How did you resolve the situation?",
        "When leading a team, how do you foster an environment that encourages collaborative work and thinking? Give me an example.",
        "Give me an example of a time when you removed a barrier that was getting in the way of getting the job done.",
    ],
    "Skills case study": [
        "Here is a job-related case study: describe how you would approach a difficult problem in this role, including the steps, trade-offs, and how you would measure success.",
        "What technical or practical decision would you make first in this case, and why?",
    ],
}


@router.post("/candidate/invite")
async def invite_candidate(payload: dict, request: Request, db: Session = Depends(get_db)):
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
        interviewer_id=None,
        status="scheduled",
        consent_status="pending",
    )
    db.add(interview)
    db.flush()

    token = uuid4().hex
    invitation = InterviewInvitation(
        company_id=company_id,
        interview_id=interview.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(invitation)
    db.commit()

    base_url = str(request.base_url).rstrip("/")
    return {
        "message": "Candidate interview invitation created",
        "invitation_url": f"{base_url}/candidate/interview/{token}",
        "share_url": f"{base_url}/candidate/interview/{token}",
        "interview_id": interview.id,
        "token": token,
    }


@router.get("/candidate/interview/{token}", response_class=HTMLResponse)
async def candidate_invitation_page(token: str, request: Request, db: Session = Depends(get_db)):
    invitation = db.query(InterviewInvitation).filter(InterviewInvitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Invitation has expired")

    interview = db.query(Interview).filter(Interview.id == invitation.interview_id).first()
    candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
    company = db.query(Company).filter(Company.id == interview.company_id).first()
    job = db.query(Job).filter(Job.id == interview.job_id).first()
    version = db.query(JobVersion).filter(JobVersion.job_id == interview.job_id).order_by(JobVersion.version_number.desc()).first()
    criteria = []
    if version:
        try:
            criteria = json.loads(version.competencies_json or "[]")
        except (TypeError, ValueError):
            criteria = []

    with open("app/templates/candidate_interview.html", "r", encoding="utf-8") as f:
        content = f.read()
        content = content.replace("{{CANDIDATE_NAME}}", candidate.full_name)
        content = content.replace("{{COMPANY_NAME}}", company.name)
        content = content.replace("{{JOB_TITLE}}", job.title if job else "Interview")
        criteria_text = ", ".join(str(item.get("name", item)) if isinstance(item, dict) else str(item) for item in criteria)
        content = content.replace("{{CRITERIA}}", json.dumps(criteria_text)[1:-1])
        content = content.replace("{{INTERVIEW_AREAS}}", json.dumps(INTERVIEW_AREAS))
        content = content.replace("{{TOKEN}}", token)
        content = content.replace("{{INTERVIEW_STATUS}}", interview.status)
        return HTMLResponse(content=content)


@router.get("/candidate/interview/{token}/details")
async def candidate_invitation_details(token: str, request: Request, db: Session = Depends(get_db)):
    invitation = db.query(InterviewInvitation).filter(InterviewInvitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    interview = db.query(Interview).filter(Interview.id == invitation.interview_id).first()
    candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
    company = db.query(Company).filter(Company.id == interview.company_id).first()
    base_url = str(request.base_url).rstrip("/")
    return {
        "candidate_name": candidate.full_name,
        "company_name": company.name,
        "job_title": "Senior Product Engineer",
        "duration_minutes": 30,
        "consent_required": True,
        "interview_url": f"{base_url}/candidate/interview/{token}",
    }


@router.post("/candidate/interview/{token}/start")
async def candidate_interview_start(token: str, payload: dict, db: Session = Depends(get_db)):
    invitation = db.query(InterviewInvitation).filter(InterviewInvitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    interview = db.query(Interview).filter(Interview.id == invitation.interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    if interview.status in {"completed", "ended"}:
        raise HTTPException(status_code=409, detail="This interview is already closed")

    consented = bool(payload.get("consented", False))
    human_review_requested = bool(payload.get("human_review_requested", False))

    interview.status = "in_progress"
    interview.started_at = datetime.utcnow()
    interview.consent_status = "consented" if consented else "declined"

    existing_consent = db.query(ConsentRecord).filter(ConsentRecord.interview_id == interview.id).first()
    if existing_consent:
        existing_consent.consented = consented
        existing_consent.privacy_notice_accepted = consented
        existing_consent.human_review_requested = human_review_requested
    else:
        db.add(
            ConsentRecord(
                interview_id=interview.id,
                consented=consented,
                privacy_notice_accepted=consented,
                human_review_requested=human_review_requested,
            )
        )

    db.commit()
    return {
        "message": "Interview started",
        "status": interview.status,
        "consented": consented,
        "interview_id": interview.id,
    }


@router.post("/candidate/interview/{token}/complete")
async def candidate_interview_complete(token: str, payload: dict, db: Session = Depends(get_db)):
    invitation = db.query(InterviewInvitation).filter(InterviewInvitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    interview = db.query(Interview).filter(Interview.id == invitation.interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    requested_status = payload.get("status", "completed")
    if requested_status not in {"completed", "ended"}:
        raise HTTPException(status_code=400, detail="status must be completed or ended")

    if interview.status not in {"completed", "ended"}:
        interview.status = requested_status
        interview.completed_at = datetime.utcnow()
        invitation.used = True
        db.commit()

    return {
        "message": "Interview closed",
        "status": interview.status,
        "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
        "interview_id": interview.id,
    }
