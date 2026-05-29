
from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field

ScoreGate = Literal["pass", "warn", "fail", "unscored"]


class DescriptionJudgeResult(BaseModel):
    rationale: str = Field(..., description="Concise justification for the scores.")
    clarity: int = Field(..., ge=0, le=100)
    specificity: int = Field(..., ge=0, le=100)
    usefulness: int = Field(..., ge=0, le=100)
    normalized_score: float = Field(..., ge=0, le=1)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ContentJudgeResult(BaseModel):
    rationale: str = Field(..., description="Concise justification for the scores.")
    completeness: int = Field(..., ge=0, le=100)
    actionability: int = Field(..., ge=0, le=100)
    technical_quality: int = Field(..., ge=0, le=100)
    documentation_quality: int = Field(..., ge=0, le=100)
    normalized_score: float = Field(..., ge=0, le=1)
    missing_elements: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class SkillEvaluationResult(BaseModel):
    schema_version: str = "skill-eval.v1"
    rubric_version: str = "skill-rubric.v1"
    skill_name: str
    category: str
    skill_path: str
    skill_sha256: Optional[str] = None
    evaluated_files: list[str] = Field(default_factory=list)
    description_judge: DescriptionJudgeResult
    content_judge: ContentJudgeResult
    impact_score: Optional[int] = Field(None, ge=0, le=100)
    compatibility_score: Optional[int] = Field(None, ge=0, le=100)
    community_score: Optional[int] = Field(None, ge=0, le=100)
    overall_score: int = Field(..., ge=0, le=100)
    quality_gate: ScoreGate
    confidence: float = Field(..., ge=0, le=1)
    requires_human_review: bool = False
    blocking_issues: list[str] = Field(default_factory=list)
    overall_notes: Optional[str] = None
    judge_provider: str
    judge_model: str
    raw_response_ref: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
