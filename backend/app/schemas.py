from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    case_id: str | None = None
    case_type: str = Field(min_length=2, max_length=80)
    report_source: str = Field(min_length=2, max_length=120)
    priority: str = Field(pattern="^(low|normal|high|urgent)$")
    owner: str = Field(min_length=2, max_length=100)
    concern: str = Field(min_length=8, max_length=1000)
    site_id: str = Field(min_length=2, max_length=40)
    process_step: str = Field(min_length=2, max_length=80)
    reconciliation_id: str | None = Field(default=None, max_length=80)
    simulated: Literal[True] = True


class CaseUpdate(BaseModel):
    priority: str | None = Field(default=None, pattern="^(low|normal|high|urgent)$")
    owner: str | None = Field(default=None, min_length=2, max_length=100)
    concern: str | None = Field(default=None, min_length=8, max_length=1000)
    report_summary: str | None = Field(default=None, min_length=20, max_length=4000)


class TimelineCreate(BaseModel):
    category: str = Field(pattern="^(observation|reported_statement|hypothesis|reviewer_conclusion)$")
    summary: str = Field(min_length=2, max_length=180)
    details: str = Field(min_length=2, max_length=2000)
    event_time: str | None = None


class EvidenceCreate(BaseModel):
    source_ref: str = Field(min_length=2, max_length=200)
    collector: str = Field(min_length=2, max_length=100)
    collection_time: str
    event_time: str | None = None
    file_hash: str | None = Field(default=None, max_length=128)
    notes: str = Field(default="", max_length=1000)


class EvidenceUpdate(BaseModel):
    source_ref: str | None = Field(default=None, min_length=2, max_length=200)
    collector: str | None = Field(default=None, min_length=2, max_length=100)
    collection_time: str | None = None
    event_time: str | None = None
    file_hash: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=1000)


class InterviewNoteCreate(BaseModel):
    interviewee_role: str = Field(min_length=2, max_length=100)
    interview_date: date | None = None
    topics: str = Field(min_length=2, max_length=1000)
    notes: str = Field(min_length=2, max_length=4000)


class ActionCreate(BaseModel):
    process_change: str = Field(min_length=4, max_length=500)
    owner: str = Field(min_length=2, max_length=100)
    due_date: date


class ActionUpdate(BaseModel):
    status: str = Field(pattern="^(open|in_progress|completed)$")
    verification_evidence: str | None = Field(default=None, max_length=500)


class CloseCase(BaseModel):
    resolution: str = Field(min_length=8, max_length=1000)