# OpenClaw Skill: Robot Arm Policy Control

## Purpose
Bridge OpenClaw natural-language instructions to the local `robot-policy` MCP server, then to the robot host REST API/ROS2 stack.

## Primary workflow
1. Parse user intent into one of: `pick_and_place`, `clear_desk`, `fold_laundry`.
2. Call MCP tool `list_capabilities` once per session (cache result).
3. Call `run_policy` with:
   - `task` inferred from intent,
   - `arm` default `so101`,
   - `policy_id` optional (let server resolve default if omitted),
   - `parameters` from extracted entities (object, pick zone, place zone).
4. Poll `get_execution` until terminal status (`succeeded|failed|cancelled`).
5. On success, trigger OpenClaw camera/photo path and post confirmation to Telegram.

## Prompting guardrails
- Confirm dangerous actions before execution.
- If intent is ambiguous, ask one clarifying question.
- Prefer explicit task names over free-form policy strings.

## Example mapping
- “pick up the pencil” → `task=pick_and_place`, `parameters={"object":"pencil"}`
- “clean my desk” → `task=clear_desk`
- “fold the laundry” → `task=fold_laundry`

## Example MCP calls
```json
{"tool":"run_policy","arguments":{"task":"pick_and_place","arm":"so101","parameters":{"object":"pencil"}}}
```

```json
{"tool":"get_execution","arguments":{"execution_id":"exec_123"}}
```
