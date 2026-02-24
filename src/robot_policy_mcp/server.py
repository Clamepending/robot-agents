from __future__ import annotations

import atexit
import os
from collections.abc import Callable
from typing import Any

from .policy_registry import PolicyRegistry
from .robot_api_client import RobotApiClient
from .service import RobotPolicyService


def create_service() -> RobotPolicyService:
    client = RobotApiClient(
        base_url=os.getenv("ROBOT_API_BASE_URL", "http://127.0.0.1:8080"),
        timeout_s=float(os.getenv("ROBOT_API_TIMEOUT_S", "20")),
    )
    atexit.register(client.close)
    return RobotPolicyService(robot_api_client=client, registry=PolicyRegistry())


def _tool_result(service: RobotPolicyService, fn: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        return {"ok": True, **fn(*args, **kwargs)}
    except Exception as exc:  # pragma: no cover - exercised through service.format_error tests
        return service.format_error(exc)


def create_mcp_server() -> "FastMCP":
    from mcp.server.fastmcp import FastMCP

    service = create_service()
    mcp = FastMCP("robot-policy")

    @mcp.tool()
    def list_capabilities() -> dict:
        """List supported arms and policies for robot manipulation."""
        return _tool_result(service, service.list_capabilities)

    @mcp.tool()
    def run_policy(
        task: str,
        arm: str = "so101",
        policy_id: str | None = None,
        parameters: dict | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        """Execute a task policy on a robot arm (default SO-101)."""
        return _tool_result(
            service,
            service.run_policy,
            task=task,
            arm=arm,
            policy_id=policy_id,
            parameters=parameters,
            correlation_id=correlation_id,
        )

    @mcp.tool()
    def get_execution(execution_id: str) -> dict:
        """Get status/details for a previously requested execution."""
        return _tool_result(service, service.get_execution, execution_id)

    @mcp.tool()
    def cancel_execution(execution_id: str) -> dict:
        """Cancel an execution if it is still running."""
        return _tool_result(service, service.cancel_execution, execution_id)

    return mcp


def main() -> None:
    create_mcp_server().run()


if __name__ == "__main__":
    main()
