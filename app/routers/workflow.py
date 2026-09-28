import json
import re
from io import BytesIO
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    Candidate,
    CandidateDecision,
    Company,
    CompanyMembership,
    Interview,
    InterviewInvitation,
    InterviewScore,
    Job,
    JobApplication,
    JobVersion,
    User,
)
from app.routers.auth import get_current_user
from app.services.resume_screener import get_job_criteria as criteria_for, screen_resume_text as screen_resume

router = APIRouter()


def role_for(user: User) -> str:
    if not user.memberships:
        return "Candidate"
    raw_role = user.memberships[0].role
    return "Candidate" if raw_role == "Candidate" else "Hiring Team"


def require_employer(user: User) -> None:
    if role_for(user) != "Hiring Team":
        raise HTTPException(status_code=403, detail="Hiring Team access required")


def company_for_user(user: User, db: Session) -> Company:
    company = db.query(Company).join(CompanyMembership).filter(CompanyMembership.user_id == user.id, CompanyMembership.is_active.is_(True)).first()
    if not company:
        raise HTTPException(status_code=403, detail="User is not connected to a company")
    return company


def criteria_for(job: Job, db: Session) -> list[str]:
    version = db.query(JobVersion).filter(JobVersion.job_id == job.id).order_by(JobVersion.version_number.desc()).first()
    if not version:
        return []
    values = []
    for field in (version.competencies_json, version.rubric_json):
        try:
            parsed = json.loads(field or "[]")
            values.extend(str(item.get("name", item)) if isinstance(item, dict) else str(item) for item in parsed)
        except (TypeError, ValueError):
            continue
    return [value.strip() for value in values if value.strip()]


def screen_resume(job: Job, resume_text: str, db: Session) -> tuple[float, str]:
    haystack = f"{job.description} {' '.join(criteria_for(job, db))}".lower()
    required_terms = set(re.findall(r"[a-z][a-z0-9+#.-]{2,}", haystack))
    resume_terms = set(re.findall(r"[a-z][a-z0-9+#.-]{2,}", resume_text.lower()))
    ignored = {"with", "that", "this", "from", "will", "have", "for", "and", "the", "you", "our", "are"}
    required_terms -= ignored
    matches = sorted(term for term in required_terms if term in resume_terms)
    score = round(min(100, (len(matches) / max(1, min(len(required_terms), 12))) * 100), 1)
    if not required_terms:
        score = 50.0
    reason = f"Qualification screen matched {len(matches)} role signals: {', '.join(matches[:12]) or 'no explicit signals found'}. Human review is required."
    return score, reason


@router.get("/jobs")
async def public_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.status == "published").order_by(Job.created_at.desc()).all()
    return [{"id": job.id, "title": job.title, "company": job.company.name if job.company else "", "description": job.description, "criteria": criteria_for(job, db)} for job in jobs]


@router.get("/jobs/{job_id}")
async def public_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.status == "published").first()
    if not job:
        raise HTTPException(status_code=404, detail="Published job not found")
    return {"id": job.id, "title": job.title, "company": job.company.name if job.company else "", "description": job.description, "criteria": criteria_for(job, db)}


@router.post("/employer/jobs")
async def create_job(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_employer(current_user)
    company = company_for_user(current_user, db)
    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", "")).strip()
    if not title or not description:
        raise HTTPException(status_code=400, detail="title and description are required")
    competencies = payload.get("competencies", [])
    rubric = payload.get("rubric", [])
    job = Job(company_id=company.id, title=title, description=description, status="published" if payload.get("publish") else "draft")
    db.add(job)
    db.flush()
    db.add(JobVersion(job_id=job.id, version_number=1, title=title, description=description, competencies_json=json.dumps(competencies), rubric_json=json.dumps(rubric)))
    db.commit()
    return {"id": job.id, "status": job.status, "message": "Job published" if job.status == "published" else "Job saved as draft"}


@router.post("/jobs/{job_id}/apply")
async def apply_to_job(job_id: int, resume: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if role_for(current_user) != "Candidate":
        raise HTTPException(status_code=403, detail="Candidate account required")
    job = db.query(Job).filter(Job.id == job_id, Job.status == "published").first()
    if not job:
        raise HTTPException(status_code=404, detail="Published job not found")
    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Resume must be uploaded as a PDF file")
    if resume.content_type not in {None, "application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Only PDF resumes are accepted")
    resume_bytes = await resume.read()
    if len(resume_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Resume PDF must be smaller than 10 MB")
    if not resume_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF")
    try:
        reader = PdfReader(BytesIO(resume_bytes))
        resume_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="The resume PDF could not be read") from exc
    if len(resume_text) < 40:
        raise HTTPException(status_code=400, detail="The PDF contains too little readable text. Upload a text-based PDF rather than a scanned image.")
    existing = db.query(JobApplication).join(Candidate).filter(JobApplication.job_id == job_id, Candidate.email == current_user.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="You have already applied to this job")
    candidate = db.query(Candidate).filter(Candidate.email == current_user.email, Candidate.company_id == job.company_id).first()
    if not candidate:
        candidate = Candidate(company_id=job.company_id, full_name=current_user.full_name, email=current_user.email)
        db.add(candidate)
        db.flush()
    score, reason = screen_resume(job, resume_text, db)
    qualified = score >= 50
    application = JobApplication(job_id=job.id, candidate_id=candidate.id, resume_text=resume_text, status="qualified" if qualified else "screened_out", screening_score=score, screening_reason=reason)
    db.add(application)
    db.flush()
    interview_link = None
    if qualified:
        interview = Interview(company_id=job.company_id, job_id=job.id, candidate_id=candidate.id, status="scheduled", consent_status="pending")
        db.add(interview)
        db.flush()
        invitation = InterviewInvitation(company_id=job.company_id, interview_id=interview.id, token=uuid4().hex, expires_at=datetime.utcnow() + timedelta(days=7))
        db.add(invitation)
        interview_link = f"/candidate/interview/{invitation.token}"
    db.commit()
    return {"application_id": application.id, "status": application.status, "screening_score": score, "screening_reason": reason, "interview_link": interview_link}


@router.get("/candidate/applications")
async def candidate_applications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(JobApplication, Job, Candidate).join(Job, Job.id == JobApplication.job_id).join(Candidate, Candidate.id == JobApplication.candidate_id).filter(Candidate.email == current_user.email).all()
    result = []
    for application, job, candidate in rows:
        interview = db.query(Interview).filter(Interview.job_id == job.id, Interview.candidate_id == candidate.id).first()
        invitation = db.query(InterviewInvitation).filter(InterviewInvitation.interview_id == interview.id).first() if interview else None
        decision = db.query(CandidateDecision).filter(CandidateDecision.application_id == application.id).first()
        result.append({"job": job.title, "status": application.status, "screening_score": application.screening_score, "interview_link": f"/candidate/interview/{invitation.token}" if invitation and not invitation.used else None, "decision": decision.decision if decision else "pending"})
    return result


@router.get("/candidate/dashboard")
async def candidate_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if role_for(current_user) != "Candidate":
        raise HTTPException(status_code=403, detail="Candidate account required")

    open_jobs = db.query(Job).filter(Job.status == "published").order_by(Job.created_at.desc()).all()
    inactive_jobs = db.query(Job).filter(Job.status != "published").order_by(Job.created_at.desc()).all()
    applications = db.query(JobApplication, Job, Candidate).join(Job, Job.id == JobApplication.job_id).join(Candidate, Candidate.id == JobApplication.candidate_id).filter(Candidate.email == current_user.email).order_by(JobApplication.created_at.desc()).all()
    application_rows = []
    interview_rows = []
    for application, job, candidate in applications:
        interview = db.query(Interview).filter(Interview.job_id == job.id, Interview.candidate_id == candidate.id).first()
        invitation = db.query(InterviewInvitation).filter(InterviewInvitation.interview_id == interview.id).first() if interview else None
        decision = db.query(CandidateDecision).filter(CandidateDecision.application_id == application.id).first()
        application_rows.append({
            "id": application.id,
            "job_id": job.id,
            "job": job.title,
            "company": job.company.name if job.company else "",
            "status": application.status,
            "screening_score": application.screening_score,
            "screening_reason": application.screening_reason,
            "decision": decision.decision if decision else "pending",
        })
        if interview:
            score = db.query(InterviewScore).filter(InterviewScore.interview_id == interview.id).first()
            interview_rows.append({
                "id": interview.id,
                "job": job.title,
                "company": job.company.name if job.company else "",
                "status": interview.status,
                "score": score.score if score else None,
                "interview_link": f"/candidate/interview/{invitation.token}" if invitation and not invitation.used else None,
                "started_at": interview.started_at.isoformat() if interview.started_at else None,
                "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
            })

    def job_row(job: Job) -> dict:
        return {"id": job.id, "title": job.title, "company": job.company.name if job.company else "", "description": job.description, "criteria": criteria_for(job, db), "status": job.status}

    return {"open_jobs": [job_row(job) for job in open_jobs], "inactive_jobs": [job_row(job) for job in inactive_jobs], "applications": application_rows, "interviews": interview_rows}


@router.post("/candidate/interview/{token}/score")
async def score_interview(token: str, payload: dict, db: Session = Depends(get_db)):
    invitation = db.query(InterviewInvitation).filter(InterviewInvitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    interview = db.query(Interview).filter(Interview.id == invitation.interview_id).first()
    score = max(0, min(100, float(payload.get("score", 0))))
    existing = db.query(InterviewScore).filter(InterviewScore.interview_id == interview.id).first()
    if not existing:
        existing = InterviewScore(interview_id=interview.id)
        db.add(existing)
    existing.score = score
    existing.criteria_scores_json = json.dumps(payload.get("criteria_scores", {}))
    existing.rationale = str(payload.get("rationale", "AI-generated evidence; human review required."))
    existing.source = "ai"
    db.commit()
    return {"ok": True, "score": score}


@router.get("/employer/applications")
async def employer_applications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_employer(current_user)
    company = company_for_user(current_user, db)
    rows = db.query(JobApplication, Job, Candidate).join(Job, Job.id == JobApplication.job_id).join(Candidate, Candidate.id == JobApplication.candidate_id).filter(Job.company_id == company.id).order_by(JobApplication.screening_score.desc()).all()
    result = []
    for application, job, candidate in rows:
        interview = db.query(Interview).filter(Interview.job_id == job.id, Interview.candidate_id == candidate.id).first()
        interview_score = db.query(InterviewScore).filter(InterviewScore.interview_id == interview.id).first() if interview else None
        result.append({"application_id": application.id, "candidate": candidate.full_name, "email": candidate.email, "job": job.title, "application_status": application.status, "screening_score": application.screening_score, "interview_score": interview_score.score if interview_score else None, "rank_score": interview_score.score if interview_score else application.screening_score or 0, "interview_status": interview.status if interview else None})
    return sorted(result, key=lambda item: item["rank_score"], reverse=True)


@router.post("/employer/applications/{application_id}/decision")
async def decide_application(application_id: int, payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_employer(current_user)
    decision_value = payload.get("decision")
    if decision_value not in {"passed", "failed"}:
        raise HTTPException(status_code=400, detail="decision must be passed or failed")
    application = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    company = company_for_user(current_user, db)
    job = db.query(Job).filter(Job.id == application.job_id, Job.company_id == company.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Application not found")
    decision = db.query(CandidateDecision).filter(CandidateDecision.application_id == application.id).first()
    if not decision:
        decision = CandidateDecision(application_id=application.id)
        db.add(decision)
    decision.decision = decision_value
    decision.notes = str(payload.get("notes", ""))
    decision.reviewer_id = current_user.id
    application.status = decision_value
    db.commit()
    return {"application_id": application.id, "decision": decision_value, "message": "Human decision saved"}