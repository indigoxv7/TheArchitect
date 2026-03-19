from __future__ import annotations

from src.config.tuning import battle_factor
from src.domain.combat.enums import BattleTeam, CombatRole, CommanderStance, TargetPriority
from src.domain.combat.state import BattleState, CommanderOrders


class BattleTargetingMixin:
    def _lane_distance(self, attacker, target) -> int:
        attacker_mid = getattr(attacker, "lane_start", 0) + (self._entity_lane_width(attacker) - 1) / 2.0
        target_mid = getattr(target, "lane_start", 0) + (self._entity_lane_width(target) - 1) / 2.0
        return int(abs(attacker_mid - target_mid))

    def _line_distance(self, attacker, target) -> int:
        return abs(int(getattr(attacker, "line", 0)) - int(getattr(target, "line", 0)))

    def _frontline_targets(self, battle: BattleState, team: BattleTeam) -> list:
        if team == BattleTeam.ALLY:
            return [
                entity
                for entity in self._active_enemies(battle)
                if int(getattr(entity, "line", 0)) == battle.enemy_front_line
            ]
        return [
            entity
            for entity in self._active_allies(battle)
            if int(getattr(entity, "line", 0)) == battle.player_front_line
        ]

    def _select_target(self, battle: BattleState, attacker, candidates: list, orders: CommanderOrders | None = None):
        if not candidates or attacker is None:
            return None
        priority = orders.target_priority if orders is not None else TargetPriority.FRONTLINE
        alive = [candidate for candidate in candidates if self._entity_health(candidate) > 0.0]
        if not alive:
            return None

        def common_key(candidate):
            role_rank = 2
            if getattr(candidate, "role", CombatRole.FRONTLINE) == CombatRole.FRONTLINE:
                role_rank = 0
            elif getattr(candidate, "role", CombatRole.FRONTLINE) == CombatRole.RANGED:
                role_rank = 1
            health_ratio = self._entity_health(candidate) / max(1.0, self._entity_max_health(candidate))
            return (
                role_rank,
                health_ratio,
                self._line_distance(attacker, candidate),
                self._lane_distance(attacker, candidate),
                self._entity_name(candidate),
            )

        if priority == TargetPriority.WEAKEST:
            return min(
                alive,
                key=lambda candidate: (
                    self._entity_health(candidate) / max(1.0, self._entity_max_health(candidate)),
                    self._line_distance(attacker, candidate),
                    self._lane_distance(attacker, candidate),
                ),
            )
        if priority == TargetPriority.STRONGEST:
            return max(
                alive,
                key=lambda candidate: (
                    self._entity_health(candidate),
                    -self._line_distance(attacker, candidate),
                    -self._lane_distance(attacker, candidate),
                ),
            )
        if priority == TargetPriority.SUPPORT:
            return sorted(
                alive,
                key=lambda candidate: (
                    getattr(candidate, "role", CombatRole.FRONTLINE) != CombatRole.SUPPORT,
                    common_key(candidate),
                ),
            )[0]
        if priority == TargetPriority.RANGED:
            return sorted(
                alive,
                key=lambda candidate: (
                    getattr(candidate, "role", CombatRole.FRONTLINE) != CombatRole.RANGED,
                    common_key(candidate),
                ),
            )[0]
        close = [candidate for candidate in alive if self._line_distance(attacker, candidate) <= 1]
        return sorted(close or alive, key=common_key)[0]

    def _stance_attack_bonus(self, orders: CommanderOrders | None) -> float:
        if orders is None:
            return 0.0
        if orders.stance == CommanderStance.ADVANCE:
            return battle_factor("stance_advance_attack_bonus", 0.03)
        if orders.stance == CommanderStance.AGGRESSIVE:
            return battle_factor("stance_aggressive_attack_bonus", 0.05)
        if orders.stance == CommanderStance.DEFENSIVE:
            return battle_factor("stance_defensive_attack_bonus", -0.03)
        return 0.0

    def _ranged_penalties(self, battle: BattleState, attacker, target) -> tuple[float, float, float]:
        congestion_penalty = (
            battle_factor("ranged_congestion_penalty", 0.05) if self._entity_lane_width(attacker) > 1 else 0.0
        )
        line_distance = self._line_distance(attacker, target)
        range_penalty = max(0.0, battle_factor("ranged_range_penalty_per_line", 0.05) * max(0, line_distance - 1))
        firing_penalty = 0.0
        if getattr(attacker, "role", CombatRole.FRONTLINE) != CombatRole.FRONTLINE:
            frontline_enemy = self._frontline_targets(battle, getattr(attacker, "team", BattleTeam.ALLY))
            if any(self._lane_distance(attacker, enemy) == 0 for enemy in frontline_enemy):
                firing_penalty = battle_factor("ranged_firing_through_engagement_penalty", 0.1)
        return congestion_penalty, firing_penalty, range_penalty
