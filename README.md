# Robot Policy MCP Server (OpenClaw ↔ SO-101)

This repository implements a **robot-policy MCP server** so OpenClaw can turn natural-language instructions (e.g., from Telegram) into structured policy executions on physical robot arms, with first-class support for the **SO-101** arm.

## Detailed Plan (Phase 1 first, extensible to Phase 2)

### 1) Architecture

1. **User command path**: Telegram → OpenClaw agent → OpenClaw skill → MCP tool calls.
2. **Control path**: MCP server validates command and selected policy, then calls a local robot REST API on the robot host machine.
3. **Robot execution path**: REST API adapter triggers ROS2 action server (or equivalent driver layer), executes motion/policy, and returns task state.
4. **Feedback path**: completion/failure is reported back through MCP to OpenClaw, then OpenClaw can trigger camera capture and send photo confirmation.

### 2) Phase 1 Scope

- Build and test an MCP server with tools to:
  - discover supported arms/policies,
  - run one command end-to-end (`pick_and_place`) on SO-101,
  - poll execution status,
  - cancel execution.
- Add a reusable OpenClaw skill definition (`skills/openclaw-robot-arm/SKILL.md`).
- Provide robot API contract suitable for ROS2 adapter integration.

### 3) Phase 2 Extension Points

- Register ACT/diffusion policies for desk clearing/folding tasks.
- Add online policy selection by context and confidence scoring.
- Add richer camera/event callback loop (before/after images + audit trail).

## MCP Tools

- `list_capabilities`: returns arms, tasks, and policy metadata.
- `run_policy`: executes a task on a selected arm/policy.
- `get_execution`: retrieves execution status and metadata.
- `cancel_execution`: requests cancellation.

## SO-101 Support


Response envelope for MCP tools:
- Success: `{ "ok": true, ... }`
- Errors: `{ "ok": false, "error_type": "validation_error|robot_api_http_error|robot_api_connection_error|internal_error", ... }`

The default arm profile includes:
- arm id: `so101`
- supported tasks: `pick_and_place`, `clear_desk`, `fold_laundry`
- default policy for phase 1: `so101_pick_and_place_v1`

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

## Running the MCP server

```bash
robot-policy-mcp
```

Environment variables:
- `ROBOT_API_BASE_URL` (default: `http://127.0.0.1:8080`)
- `ROBOT_API_TIMEOUT_S` (default: `20`)


## Cloud deployment (Docker)

Build MCP server image:

```bash
docker build -t robot-policy-mcp:latest -f Dockerfile .
```

Build mock robot API image (for integration/staging):

```bash
docker build -t robot-api-mock:latest -f Dockerfile.mock-robot-api .
```

Run both with compose:

```bash
docker compose -f deploy/docker-compose.yml up --build
```

Run one-command Docker validation:

```bash
./scripts/docker_selftest.sh
```

If your environment is unprivileged (common in CI sandboxes), `dockerd` may not stay up; the script exits with code `2` and points to daemon logs.

## E2E latency smoke test

Run mock API:

```bash
uvicorn robot_policy_mcp.mock_robot_api:app --host 127.0.0.1 --port 8080
```

Then run latency checks against the real request flow:

```bash
python scripts/run_e2e_latency_check.py --base-url http://127.0.0.1:8080 --runs 10
```

## Robot API contract (expected)

- `POST /v1/executions`
  - request: `{ task, arm, policy_id, parameters, correlation_id }`
  - response: `{ execution_id, status, accepted_at }`
- `GET /v1/executions/{execution_id}`
  - response: `{ execution_id, status, started_at, finished_at, result, error }`
- `POST /v1/executions/{execution_id}/cancel`
  - response: `{ execution_id, status }`

This contract is intentionally simple so the robot host can implement it as a thin ROS2 adapter around action goals.
