from datetime import datetime, timezone

import httpx
import pytest

from robot_policy_mcp.models import ExecutionCreated, ExecutionDetails, ExecutionRequest, ExecutionStatus
from robot_policy_mcp.policy_registry import PolicyRegistry
from robot_policy_mcp.robot_api_client import RobotApiClient
from robot_policy_mcp.service import RobotPolicyService


class FakeRobotApiClient:
    def __init__(self) -> None:
        self.last_request = None

    def create_execution(self, request):
        self.last_request = request
        return ExecutionCreated(
            execution_id="exec_1",
            status=ExecutionStatus.queued,
            accepted_at=datetime.now(tz=timezone.utc),
        )

    def get_execution(self, execution_id: str):
        return ExecutionDetails(
            execution_id=execution_id,
            status=ExecutionStatus.running,
            started_at=datetime.now(tz=timezone.utc),
        )

    def cancel_execution(self, execution_id: str):
        return {"execution_id": execution_id, "status": "cancelled"}


def test_run_policy_resolves_default_so101_policy_and_merges_defaults():
    client = FakeRobotApiClient()
    service = RobotPolicyService(robot_api_client=client)

    result = service.run_policy(
        task="pick_and_place",
        arm="so101",
        parameters={"object": "pencil", "pick_zone": "front_center"},
    )

    assert result["resolved_policy_id"] == "so101_pick_and_place_v1"
    assert result["effective_parameters"]["grasp_style"] == "top_down"
    assert result["effective_parameters"]["pick_zone"] == "front_center"
    assert client.last_request.policy_id == "so101_pick_and_place_v1"
    assert client.last_request.parameters["object"] == "pencil"


def test_get_and_cancel_execution():
    client = FakeRobotApiClient()
    service = RobotPolicyService(robot_api_client=client)

    details = service.get_execution("exec_7")
    cancelled = service.cancel_execution("exec_7")

    assert details["execution_id"] == "exec_7"
    assert details["status"] == "running"
    assert cancelled["status"] == "cancelled"


def test_reject_invalid_policy_for_task():
    client = FakeRobotApiClient()
    service = RobotPolicyService(robot_api_client=client)

    with pytest.raises(ValueError, match="not valid"):
        service.run_policy(
            task="pick_and_place",
            arm="so101",
            policy_id="so101_fold_laundry_act_v1",
        )


def test_reject_unknown_arm_and_task_combination():
    registry = PolicyRegistry()

    with pytest.raises(ValueError, match="Unknown arm"):
        registry.resolve_policy_id(task="pick_and_place", arm="so999", requested_policy_id=None)

    with pytest.raises(ValueError, match="not supported"):
        registry.resolve_policy_id(task="wipe_table", arm="so101", requested_policy_id=None)


def test_format_error_shapes_validation_and_http_errors():
    service = RobotPolicyService(robot_api_client=FakeRobotApiClient())

    validation = service.format_error(ValueError("bad input"))
    assert validation["error_type"] == "validation_error"

    req = httpx.Request("GET", "http://robot/v1/executions/x")
    resp = httpx.Response(404, text="not found", request=req)
    http_exc = httpx.HTTPStatusError("404", request=req, response=resp)

    formatted = service.format_error(http_exc)
    assert formatted["error_type"] == "robot_api_http_error"
    assert formatted["status_code"] == 404


def test_robot_api_client_success_flow_with_mock_transport():
    now = datetime.now(tz=timezone.utc).isoformat()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/executions":
            return httpx.Response(
                200,
                json={"execution_id": "exec_42", "status": "queued", "accepted_at": now},
                request=request,
            )
        if request.method == "GET" and request.url.path == "/v1/executions/exec_42":
            return httpx.Response(
                200,
                json={"execution_id": "exec_42", "status": "running", "started_at": now},
                request=request,
            )
        if request.method == "POST" and request.url.path == "/v1/executions/exec_42/cancel":
            return httpx.Response(200, json={"execution_id": "exec_42", "status": "cancelled"}, request=request)
        return httpx.Response(500, json={"error": "unexpected"}, request=request)

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://robot.test")
    client = RobotApiClient(base_url="http://robot.test", client=http_client)

    created = client.create_execution(ExecutionRequest(task="pick_and_place", arm="so101"))
    details = client.get_execution("exec_42")
    cancelled = client.cancel_execution("exec_42")

    assert created.execution_id == "exec_42"
    assert details.status == ExecutionStatus.running
    assert cancelled["status"] == "cancelled"

    client.close()
