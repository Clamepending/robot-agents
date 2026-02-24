from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class CreateExecutionRequest(BaseModel):
    task: str
    arm: str
    policy_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class ExecutionRecord(BaseModel):
    execution_id: str
    status: str
    accepted_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


app = FastAPI(title="Mock Robot API", version="0.1.0")
EXECUTIONS: dict[str, ExecutionRecord] = {}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/executions")
async def create_execution(payload: CreateExecutionRequest) -> dict[str, Any]:
    execution_id = f"exec_{uuid4().hex[:12]}"
    now = datetime.now(tz=timezone.utc)
    rec = ExecutionRecord(execution_id=execution_id, status="queued", accepted_at=now)
    EXECUTIONS[execution_id] = rec

    async def run_job() -> None:
        await asyncio.sleep(0.02)
        if execution_id not in EXECUTIONS:
            return
        current = EXECUTIONS[execution_id]
        current.status = "running"
        current.started_at = datetime.now(tz=timezone.utc)
        await asyncio.sleep(0.08)
        if execution_id not in EXECUTIONS:
            return
        current = EXECUTIONS[execution_id]
        if current.status == "cancelled":
            current.finished_at = datetime.now(tz=timezone.utc)
            return
        current.status = "succeeded"
        current.finished_at = datetime.now(tz=timezone.utc)
        current.result = {
            "task": payload.task,
            "arm": payload.arm,
            "policy_id": payload.policy_id,
            "parameters": payload.parameters,
        }

    asyncio.create_task(run_job())

    return {
        "execution_id": execution_id,
        "status": "queued",
        "accepted_at": now,
    }


@app.get("/v1/executions/{execution_id}")
def get_execution(execution_id: str) -> dict[str, Any]:
    rec = EXECUTIONS.get(execution_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Execution not found")
    return rec.model_dump(mode="json")


@app.post("/v1/executions/{execution_id}/cancel")
def cancel_execution(execution_id: str) -> dict[str, Any]:
    rec = EXECUTIONS.get(execution_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Execution not found")
    if rec.status in {"succeeded", "failed", "cancelled"}:
        return {"execution_id": execution_id, "status": rec.status}
    rec.status = "cancelled"
    rec.finished_at = datetime.now(tz=timezone.utc)
    return {"execution_id": execution_id, "status": "cancelled"}
