from pydantic import BaseModel, EmailStr


class CandidateInviteRequest(BaseModel):
    company_id: int
    candidate_name: str
    candidate_email: EmailStr
    job_id: int = 1


class ApplicationDecisionRequest(BaseModel):
    decision: str
    notes: str = ""
