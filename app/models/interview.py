from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    interviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    consent_status: Mapped[str] = mapped_column(String(50), default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class InterviewInvitation(Base):
    __tablename__ = "interview_invitations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    assemblyai_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transcript_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    session_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    consented: Mapped[bool] = mapped_column(Boolean, default=False)
    privacy_notice_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    human_review_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    accommodation_requested: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class InterviewScore(Base):
    __tablename__ = "interview_scores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), unique=True, index=True)
    score: Mapped[float] = mapped_column(default=0)
    criteria_scores_json: Mapped[str] = mapped_column(Text, default="{}")
    rationale: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(50), default="ai")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcripts.id"), index=True)
    speaker: Mapped[str] = mapped_column(String(50), default="candidate")
    text: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class EvaluationDraft(Base):
    __tablename__ = "evaluation_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    competency: Mapped[str] = mapped_column(String(255))
    evidence: Mapped[str] = mapped_column(Text)
    evidence_strength: Mapped[str] = mapped_column(String(50), default="limited")
    unanswered_questions: Mapped[str] = mapped_column(Text, default="")
    follow_up: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"), index=True)
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision: Mapped[str] = mapped_column(String(100), default="review-pending")
    notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
