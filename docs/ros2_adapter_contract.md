# ROS2 Adapter Contract Notes (SO-101)

This document defines how a robot-host process should map REST requests from `robot-policy-mcp` to ROS2 actions.

## Suggested mapping

- `task=pick_and_place`
  - Action server: `/so101/pick_place`
  - Goal fields: `object_label`, `pick_pose`, `place_pose`, `grasp_style`
- `task=clear_desk`
  - Action server: `/so101/clear_desk`
- `task=fold_laundry`
  - Action server: `/so101/fold_laundry`

## Status mapping

- ROS2 `ACCEPTED` -> `queued`
- ROS2 `EXECUTING` -> `running`
- ROS2 `SUCCEEDED` -> `succeeded`
- ROS2 `ABORTED` -> `failed`
- ROS2 `CANCELED` -> `cancelled`

## Minimal implementation approach

1. FastAPI server on robot host exposing `/v1/executions*` endpoints.
2. Keep a local execution table keyed by `execution_id`.
3. Dispatch ROS2 goals on create.
4. Update execution table from ROS2 feedback/result callbacks.
