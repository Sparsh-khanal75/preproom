"""Interview pack schema. A pack is the only place interview-type knowledge lives."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SUBSCORES = ("consistency", "specificity", "relevance", "fluency", "language")
Trigger = Literal["short", "no_specifics", "contradiction", "off_topic"]


class ProfileField(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    label: str
    type: Literal["text", "textarea", "number", "list", "select"] = "text"
    required: bool = True
    options: list[str] = []
    placeholder: str = ""
    help: str = ""
    entity: bool = False  # a name that should be stated exactly (university, company...)


class Question(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,59}$")
    text: str
    topic: str
    expects: list[str] = []  # keywords a relevant answer usually touches
    profile_fields: list[str] = []  # facts this answer should agree with
    follow_up_if: list[Trigger] = ["short", "no_specifics"]
    follow_ups: list[str] = []  # fallback follow-up questions if no LLM is available
    required: bool = False


class Pack(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,79}$")
    name: str
    version: int = 1
    category: Literal["visa", "admission", "job", "custom"] = "custom"
    description: str
    persona: str
    session_length: int = Field(8, ge=3, le=20)
    max_follow_ups: int = Field(1, ge=0, le=3)
    min_answer_words: int = Field(25, ge=5, le=200)
    profile_fields: list[ProfileField]
    questions: list[Question] = Field(min_length=3)
    rubric: dict[str, float]
    generic_answers: list[str] = []
    tips: dict[str, str] = {}
    honesty_note: str = (
        "Practise telling your own true story clearly. PrepRoom never writes answers for you, "
        "and a real interviewer will notice memorised or invented answers."
    )

    @field_validator("rubric")
    @classmethod
    def _rubric(cls, v: dict[str, float]) -> dict[str, float]:
        unknown = set(v) - set(SUBSCORES)
        if unknown:
            raise ValueError(f"unknown rubric keys: {sorted(unknown)}; allowed: {list(SUBSCORES)}")
        total = sum(v.values())
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"rubric weights must sum to 1.0 (got {total:.2f})")
        return v

    @model_validator(mode="after")
    def _references(self) -> Pack:
        fields = {f.id for f in self.profile_fields}
        ids = [q.id for q in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("question ids must be unique")
        for q in self.questions:
            missing = set(q.profile_fields) - fields
            missing |= set(re.findall(r"{(\w+)}", q.text)) - fields
            if missing:
                raise ValueError(f"question '{q.id}' references unknown profile fields {sorted(missing)}")
        if self.session_length > len(self.questions):
            raise ValueError("session_length is larger than the number of questions")
        return self
