from __future__ import annotations

from .models import ArmProfile, PolicySpec


DEFAULT_ARM = "so101"


class PolicyRegistry:
    """In-memory registry for robot arms and task policies."""

    def __init__(self) -> None:
        self._arms: dict[str, ArmProfile] = {
            DEFAULT_ARM: ArmProfile(
                arm=DEFAULT_ARM,
                description="SO-101 tabletop manipulator arm",
                dof=6,
                tasks=["pick_and_place", "clear_desk", "fold_laundry"],
            )
        }
        self._policies: dict[str, PolicySpec] = {
            "so101_pick_and_place_v1": PolicySpec(
                policy_id="so101_pick_and_place_v1",
                arm=DEFAULT_ARM,
                task="pick_and_place",
                model_type="scripted",
                description="Reliable phase-1 pick and place baseline policy",
                default_parameters={"pick_zone": "front_left", "place_zone": "rear_right", "grasp_style": "top_down"},
            ),
            "so101_clear_desk_diffusion_v1": PolicySpec(
                policy_id="so101_clear_desk_diffusion_v1",
                arm=DEFAULT_ARM,
                task="clear_desk",
                model_type="diffusion",
                description="Desk-clearing manipulation policy",
            ),
            "so101_fold_laundry_act_v1": PolicySpec(
                policy_id="so101_fold_laundry_act_v1",
                arm=DEFAULT_ARM,
                task="fold_laundry",
                model_type="act",
                description="Laundry folding policy for staged cloth configurations",
            ),
        }

    def list_arms(self) -> list[ArmProfile]:
        return list(self._arms.values())

    def list_policies(self, *, arm: str | None = None, task: str | None = None) -> list[PolicySpec]:
        return [p for p in self._policies.values() if (not arm or p.arm == arm) and (not task or p.task == task)]

    def get_arm(self, arm: str) -> ArmProfile:
        try:
            return self._arms[arm]
        except KeyError as exc:
            known = ", ".join(sorted(self._arms.keys()))
            raise ValueError(f"Unknown arm: {arm}. Known arms: {known}") from exc

    def validate_task_for_arm(self, arm: str, task: str) -> None:
        arm_profile = self.get_arm(arm)
        if task not in arm_profile.tasks:
            raise ValueError(f"Task '{task}' is not supported by arm '{arm}'. Supported tasks: {', '.join(arm_profile.tasks)}")

    def get_policy(self, policy_id: str) -> PolicySpec:
        try:
            return self._policies[policy_id]
        except KeyError as exc:
            raise ValueError(f"Unknown policy_id: {policy_id}") from exc

    def resolve_policy_id(self, task: str, arm: str, requested_policy_id: str | None) -> str:
        self.validate_task_for_arm(arm=arm, task=task)
        if requested_policy_id is None:
            matches = self.list_policies(arm=arm, task=task)
            if not matches:
                raise ValueError(f"No policy registered for arm={arm}, task={task}")
            return matches[0].policy_id

        policy = self.get_policy(requested_policy_id)
        if policy.arm != arm or policy.task != task:
            raise ValueError(f"Policy {requested_policy_id} is not valid for arm={arm}, task={task}")
        return requested_policy_id
