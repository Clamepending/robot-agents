from __future__ import annotations

import argparse
import statistics
import time

from robot_policy_mcp.robot_api_client import RobotApiClient
from robot_policy_mcp.service import RobotPolicyService


def run_once(service: RobotPolicyService, poll_interval_s: float) -> float:
    start = time.perf_counter()
    created = service.run_policy(
        task="pick_and_place",
        arm="so101",
        parameters={"object": "pencil", "pick_zone": "front_left"},
    )
    execution_id = created["execution"]["execution_id"]

    while True:
        details = service.get_execution(execution_id)
        if details["status"] in {"succeeded", "failed", "cancelled"}:
            break
        time.sleep(poll_interval_s)

    end = time.perf_counter()
    return end - start


def main() -> None:
    parser = argparse.ArgumentParser(description="Run E2E latency checks against robot-policy flow")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--poll-interval", type=float, default=0.02)
    parser.add_argument("--warn-p95-ms", type=float, default=450.0)
    args = parser.parse_args()

    client = RobotApiClient(base_url=args.base_url, timeout_s=5)
    service = RobotPolicyService(robot_api_client=client)

    latencies = []
    for _ in range(args.runs):
        latencies.append(run_once(service, args.poll_interval))

    client.close()

    lat_ms = [x * 1000.0 for x in latencies]
    p50 = statistics.median(lat_ms)
    p95 = statistics.quantiles(lat_ms, n=20)[18] if len(lat_ms) >= 2 else lat_ms[0]
    avg = sum(lat_ms) / len(lat_ms)

    print(f"runs={args.runs} avg_ms={avg:.2f} p50_ms={p50:.2f} p95_ms={p95:.2f}")
    if p95 > args.warn_p95_ms:
        raise SystemExit(f"P95 latency too high: {p95:.2f}ms > {args.warn_p95_ms:.2f}ms")


if __name__ == "__main__":
    main()
