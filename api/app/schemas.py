"""Request/response models (also the source of the generated TypeScript client)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: Literal["candidate", "coach", "admin"]


class PackSummary(BaseModel):
    slug: str
    name: str
    category: str
    description: str
    session_length: int
    question_count: int
    builtin: bool
    active: bool


class ProfileFieldOut(BaseModel):
    id: str
    label: str
    type: str
    required: bool
    options: list[str]
    placeholder: str
    help: str


class PackDetail(PackSummary):
    persona: str
    honesty_note: str
    profile_fields: list[ProfileFieldOut]
    rubric: dict[str, float]


class PackUpload(BaseModel):
    yaml: str = Field(max_length=200_000)


class ProfileIn(BaseModel):
    data: dict[str, Any]


class ProfileOut(BaseModel):
    pack_slug: str
    data: dict[str, Any]
    missing: list[str]


class StartSession(BaseModel):
    pack: str


class AnswerText(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class TurnOut(BaseModel):
    id: int
    index: int
    question_id: str
    question_text: str
    is_follow_up: bool
    answer_text: str | None
    answer_mode: str | None
    has_audio: bool
    status: str
    metrics: dict[str, Any] | None
    scores: dict[str, Any] | None


class SessionOut(BaseModel):
    id: int
    user_id: int
    pack_slug: str
    pack_name: str
    status: str
    overall_score: float | None
    started_at: datetime
    finished_at: datetime | None
    planned_questions: int
    turns: list[TurnOut]
    report: dict[str, Any] | None


class SessionSummary(BaseModel):
    id: int
    pack_slug: str
    pack_name: str
    status: str
    overall_score: float | None
    started_at: datetime
    answered: int


class ProgressOut(BaseModel):
    sessions: list[SessionSummary]
    trend: list[dict[str, Any]]
    subscore_averages: dict[str, float]
    weakest: list[str]
    totals: dict[str, Any]


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    turn_id: int
    author_name: str
    author_role: str
    body: str
    created_at: datetime


class CoachAccessIn(BaseModel):
    coach_email: EmailStr


class CandidateOut(BaseModel):
    id: int
    name: str
    email: str
    sessions: int
    last_score: float | None
    average_score: float | None


class RoleIn(BaseModel):
    role: Literal["candidate", "coach", "admin"]
