from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class PolicySpec(BaseModel):
    policy_id: str
    arm: str
    task: str
    model_type: str = Field(description="e.g., scripted, act, diffusion")
    description: str
    default_parameters: dict[str, Any] = Field(default_factory=dict)


class ArmProfile(BaseModel):
    arm: str
    description: str
    dof: int
    tasks: list[str]


class ExecutionRequest(BaseModel):
    task: str
    arm: str = "so101"
    policy_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class ExecutionCreated(BaseModel):
    execution_id: str
    status: ExecutionStatus
    accepted_at: datetime


class ExecutionDetails(BaseModel):
    execution_id: str
    status: ExecutionStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
