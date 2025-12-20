from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AnalysisTaskResponse(BaseModel):
    session_id: UUID
    status: str
    task_id: str | None


class AnalysisResponse(BaseModel):
    id: UUID
    session_id: UUID
    status: str
    confidence: float | None
    summary: str | None
    severity_suggestion: str | None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    root_cause: dict[str, Any] = Field(default_factory=dict)
    duplicate_check: dict[str, Any] = Field(default_factory=dict)
    coverage_note: str | None
    data_sensitivity_warning: str | None
    error_message: str | None
    task_id: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DuplicateCheckResponse(BaseModel):
    session_id: UUID
    duplicate_check: dict[str, Any]
