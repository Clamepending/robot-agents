from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from .models import ExecutionCreated, ExecutionDetails, ExecutionRequest


class RobotApiClient:
    def __init__(
        self,
        base_url: str,
        timeout_s: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout_s)

    def close(self) -> None:
        self._client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.3), reraise=True)
    def create_execution(self, request: ExecutionRequest) -> ExecutionCreated:
        response = self._client.post("/v1/executions", json=request.model_dump())
        response.raise_for_status()
        return ExecutionCreated.model_validate(response.json())

    def get_execution(self, execution_id: str) -> ExecutionDetails:
        response = self._client.get(f"/v1/executions/{execution_id}")
        response.raise_for_status()
        return ExecutionDetails.model_validate(response.json())

    def cancel_execution(self, execution_id: str) -> dict[str, Any]:
        response = self._client.post(f"/v1/executions/{execution_id}/cancel")
        response.raise_for_status()
        return response.json()
