import json
import re
from sqlalchemy.orm import Session

from app.models.job import Job, JobVersion


def get_job_criteria(job: Job, db: Session) -> list[str]:
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


def screen_resume_text(job: Job, resume_text: str, db: Session) -> tuple[float, str]:
    haystack = f"{job.description} {' '.join(get_job_criteria(job, db))}".lower()
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
