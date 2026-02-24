from __future__ import annotations

from typing import Any

import httpx

from .models import ExecutionRequest
from .policy_registry import PolicyRegistry
from .robot_api_client import RobotApiClient


class RobotPolicyService:
    def __init__(self, robot_api_client: RobotApiClient, registry: PolicyRegistry | None = None) -> None:
        self.registry = registry or PolicyRegistry()
        self.robot_api_client = robot_api_client

    def list_capabilities(self) -> dict[str, Any]:
        return {
            "arms": [a.model_dump() for a in self.registry.list_arms()],
            "policies": [p.model_dump() for p in self.registry.list_policies()],
        }

    def run_policy(
        self,
        *,
        task: str,
        arm: str = "so101",
        policy_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        resolved_policy_id = self.registry.resolve_policy_id(task=task, arm=arm, requested_policy_id=policy_id)
        policy = self.registry.get_policy(resolved_policy_id)
        effective_parameters = {**policy.default_parameters, **(parameters or {})}

        created = self.robot_api_client.create_execution(
            ExecutionRequest(
                task=task,
                arm=arm,
                policy_id=resolved_policy_id,
                parameters=effective_parameters,
                correlation_id=correlation_id,
            )
        )
        return {
            "execution": created.model_dump(mode="json"),
            "resolved_policy_id": resolved_policy_id,
            "effective_parameters": effective_parameters,
        }

    def get_execution(self, execution_id: str) -> dict[str, Any]:
        return self.robot_api_client.get_execution(execution_id).model_dump(mode="json")

    def cancel_execution(self, execution_id: str) -> dict[str, Any]:
        return self.robot_api_client.cancel_execution(execution_id)

    @staticmethod
    def format_error(exc: Exception) -> dict[str, Any]:
        if isinstance(exc, ValueError):
            return {"ok": False, "error_type": "validation_error", "error": str(exc)}
        if isinstance(exc, httpx.HTTPStatusError):
            return {
                "ok": False,
                "error_type": "robot_api_http_error",
                "status_code": exc.response.status_code,
                "error": exc.response.text,
            }
        if isinstance(exc, httpx.HTTPError):
            return {"ok": False, "error_type": "robot_api_connection_error", "error": str(exc)}
        return {"ok": False, "error_type": "internal_error", "error": str(exc)}
