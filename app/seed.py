import json

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models import Company, CompanyMembership, Job, JobVersion, User


def seed_demo_data() -> None:
    db: Session = SessionLocal()
    try:
        if db.query(User).filter(User.email == "admin@interviewa.ai").first():
            company = db.query(Company).filter(Company.name == "Acme Labs").first()
            if company and not db.query(Job).filter(Job.company_id == company.id).first():
                job = Job(company_id=company.id, title="Senior Product Engineer", description="Build reliable product experiences with Python APIs, SQL, testing, and collaborative problem solving.", status="published")
                db.add(job)
                db.flush()
                db.add(JobVersion(job_id=job.id, version_number=1, title=job.title, description=job.description, competencies_json=json.dumps(["Python", "APIs", "SQL", "testing", "teamwork"]), rubric_json=json.dumps(["Clear problem solving", "Relevant technical experience"])))
                db.commit()
            return

        company = Company(name="Acme Labs", domain="acme.ai")
        db.add(company)
        db.flush()

        admin = User(
            email="admin@interviewa.ai",
            full_name="Alex Admin",
            password_hash=get_password_hash("password123"),
            is_verified=True,
            mfa_enabled=False,
        )
        recruiter = User(
            email="recruiter@interviewa.ai",
            full_name="Riley Recruiter",
            password_hash=get_password_hash("password123"),
            is_verified=True,
            mfa_enabled=False,
        )
        hiring = User(
            email="hiring@interviewa.ai",
            full_name="Harper Hiring Manager",
            password_hash=get_password_hash("password123"),
            is_verified=True,
            mfa_enabled=False,
        )
        candidate = User(
            email="candidate@interviewa.ai",
            full_name="Casey Candidate",
            password_hash=get_password_hash("password123"),
            is_verified=True,
            mfa_enabled=False,
        )
        db.add_all([admin, recruiter, hiring, candidate])
        db.flush()

        db.add_all(
            [
                CompanyMembership(company_id=company.id, user_id=admin.id, role="Hiring Team"),
                CompanyMembership(company_id=company.id, user_id=recruiter.id, role="Hiring Team"),
                CompanyMembership(company_id=company.id, user_id=hiring.id, role="Hiring Team"),
                CompanyMembership(company_id=company.id, user_id=candidate.id, role="Candidate"),
            ]
        )
        job = Job(company_id=company.id, title="Senior Product Engineer", description="Build reliable product experiences with Python APIs, SQL, testing, and collaborative problem solving.", status="published")
        db.add(job)
        db.flush()
        db.add(JobVersion(job_id=job.id, version_number=1, title=job.title, description=job.description, competencies_json=json.dumps(["Python", "APIs", "SQL", "testing", "teamwork"]), rubric_json=json.dumps(["Clear problem solving", "Relevant technical experience"])))
        db.commit()
        print("Demo data seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
