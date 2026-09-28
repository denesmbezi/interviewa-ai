from pydantic import BaseModel


class InterviewStartRequest(BaseModel):
    consented: bool = True
    human_review_requested: bool = False


class InterviewScoreRequest(BaseModel):
    score: float
    criteria_scores: dict = {}
    rationale: str = ""
