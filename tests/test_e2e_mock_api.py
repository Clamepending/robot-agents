from __future__ import annotations

import socket
import subprocess
import sys
import time

from robot_policy_mcp.robot_api_client import RobotApiClient
from robot_policy_mcp.service import RobotPolicyService


def wait_for_port(host: str, port: int, timeout_s: float = 10.0) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.3)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.05)
    raise TimeoutError(f"Port {host}:{port} did not open in time")


def test_e2e_policy_run_and_latency():
    port = 18080
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "robot_policy_mcp.mock_robot_api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        wait_for_port("127.0.0.1", port)

        client = RobotApiClient(base_url=f"http://127.0.0.1:{port}", timeout_s=5)
        service = RobotPolicyService(robot_api_client=client)

        start = time.perf_counter()
        out = service.run_policy(task="pick_and_place", arm="so101", parameters={"object": "pencil"})
        execution_id = out["execution"]["execution_id"]

        terminal = None
        while True:
            terminal = service.get_execution(execution_id)
            if terminal["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.02)

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        assert terminal is not None
        assert terminal["status"] == "succeeded"
        assert elapsed_ms < 1200.0

        client.close()
    finally:
        proc.terminate()
        proc.wait(timeout=5)
