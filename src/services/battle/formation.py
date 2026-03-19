from __future__ import annotations

from src.config.tuning import battle_factor, battle_factor_int
from src.domain.combat.enums import BattleOutcome, BattlePhase, BattleTeam, BattleTriggerType, CombatRole, EncounterType
from src.domain.combat.state import BattleState, BattleTrigger


class BattleFormationMixin:
    def _frontline_group(self, entities: list) -> list:
        return [entity for entity in entities if getattr(entity, "role", CombatRole.FRONTLINE) == CombatRole.FRONTLINE]

    def _ranged_group(self, entities: list) -> list:
        return [entity for entity in entities if getattr(entity, "role", CombatRole.FRONTLINE) != CombatRole.FRONTLINE]

    def _effective_width(self, battle: BattleState, team: BattleTeam) -> int:
        width = int(battle.width)
        if team == BattleTeam.ALLY and battle.orders.width_control_bonus > 0:
            width += min(1, int(battle.orders.width_control_bonus))
        return max(1, width)

    def _solve_formations(self, battle: BattleState):
        self._assign_team_positions(
            entities=self._active_allies(battle),
            team=BattleTeam.ALLY,
            front_line=battle.player_front_line,
            total_lines=battle.total_lines,
            width=self._effective_width(battle, BattleTeam.ALLY),
        )
        self._assign_team_positions(
            entities=self._active_enemies(battle),
            team=BattleTeam.ENEMY,
            front_line=battle.enemy_front_line,
            total_lines=battle.total_lines,
            width=self._effective_width(battle, BattleTeam.ENEMY),
        )

    def _assign_team_positions(self, entities: list, team: BattleTeam, front_line: int, total_lines: int, width: int):
        if not entities:
            return
        if team == BattleTeam.ALLY:
            accessible_lines = list(range(front_line, -1, -1))
            rear_line = max(0, front_line - 1)
        else:
            accessible_lines = list(range(front_line, total_lines))
            rear_line = min(total_lines - 1, front_line + 1)

        occupancy = {line: [False] * max(1, width) for line in accessible_lines}
        role_order = {
            CombatRole.FRONTLINE: 0,
            CombatRole.RANGED: 1,
            CombatRole.SUPPORT: 2,
        }
        sorted_entities = sorted(
            entities,
            key=lambda entity: (
                role_order.get(getattr(entity, "role", CombatRole.FRONTLINE), 0),
                -self._entity_lane_width(entity),
                self._entity_name(entity),
            ),
        )

        for entity in sorted_entities:
            preferred_line = (
                front_line if getattr(entity, "role", CombatRole.FRONTLINE) == CombatRole.FRONTLINE else rear_line
            )
            line_candidates = [preferred_line] + [line for line in accessible_lines if line != preferred_line]
            placed = False
            entity_width = self._entity_lane_width(entity)
            for line in line_candidates:
                if line not in occupancy:
                    continue
                lane = self._find_open_lane(occupancy[line], entity_width)
                if lane is None:
                    continue
                self._occupy_lanes(occupancy[line], lane, entity_width)
                entity.line = line
                entity.lane_start = lane
                entity.lane_width = entity_width
                placed = True
                break
            if not placed:
                entity.line = accessible_lines[-1]
                entity.lane_start = 0
                entity.lane_width = entity_width

    @staticmethod
    def _find_open_lane(row: list[bool], lane_width: int) -> int | None:
        if lane_width >= len(row):
            return 0 if not any(row) else None
        for lane in range(0, len(row) - lane_width + 1):
            if not any(row[lane : lane + lane_width]):
                return lane
        return None

    @staticmethod
    def _occupy_lanes(row: list[bool], lane_start: int, lane_width: int):
        end = min(len(row), lane_start + lane_width)
        for index in range(lane_start, end):
            row[index] = True

    def _team_strength_on_front(self, entities: list, front_line: int) -> float:
        total = 0.0
        for entity in entities:
            if int(getattr(entity, "line", 0)) != int(front_line):
                continue
            total += self._entity_health(entity) * (
                1.0 + battle_factor("front_line_attack_count_weight", 0.10) * self._entity_attack_count(entity)
            )
        return total

    def _broken_lane_count(self, battle: BattleState, team: BattleTeam) -> int:
        front_line = battle.player_front_line if team == BattleTeam.ALLY else battle.enemy_front_line
        width = self._effective_width(battle, team)
        occupied = [False] * max(1, width)
        entities = self._active_allies(battle) if team == BattleTeam.ALLY else self._active_enemies(battle)
        for entity in entities:
            if int(getattr(entity, "line", 0)) != int(front_line):
                continue
            start = max(0, int(getattr(entity, "lane_start", 0) or 0))
            end = min(len(occupied), start + self._entity_lane_width(entity))
            for lane in range(start, end):
                occupied[lane] = True
        return len([lane for lane in occupied if not lane])

    def _backline_intrusion(self, battle: BattleState, team: BattleTeam) -> int:
        if team == BattleTeam.ALLY:
            return (
                1
                if any(
                    int(getattr(enemy, "line", 0)) < int(battle.player_front_line)
                    for enemy in self._active_enemies(battle)
                )
                else 0
            )
        return (
            1
            if any(int(getattr(ally, "line", 0)) > int(battle.enemy_front_line) for ally in self._active_allies(battle))
            else 0
        )

    def _advance_front(self, battle: BattleState, team: BattleTeam, highlights: list[str]):
        if team == BattleTeam.ALLY:
            battle.player_front_line += 1
            battle.enemy_front_line += 1
            highlights.append("The allied line advances.")
        else:
            battle.player_front_line -= 1
            battle.enemy_front_line -= 1
            highlights.append("The enemy line advances.")

    def _apply_recentering(
        self, battle: BattleState, player_progress: bool, enemy_progress: bool, highlights: list[str]
    ):
        player_missing = max(0, int(battle.default_player_front_line) - int(battle.player_front_line))
        enemy_missing = max(0, int(battle.enemy_front_line) - int(battle.default_enemy_front_line))
        player_broken = self._broken_lane_count(battle, BattleTeam.ALLY)
        enemy_broken = self._broken_lane_count(battle, BattleTeam.ENEMY)
        player_intrusion = self._backline_intrusion(battle, BattleTeam.ALLY)
        enemy_intrusion = self._backline_intrusion(battle, BattleTeam.ENEMY)

        battle.player_recenter_pressure += player_missing + player_broken + player_intrusion
        battle.enemy_recenter_pressure += enemy_missing + enemy_broken + enemy_intrusion

        threshold_base = battle_factor_int("recentering_threshold_base", 3)
        player_threshold = max(1, threshold_base - player_missing - player_broken)
        enemy_threshold = max(1, threshold_base - enemy_missing - enemy_broken)

        if (
            (player_missing > 0 or player_intrusion)
            and not enemy_progress
            and battle.player_recenter_pressure >= player_threshold
        ):
            if (
                battle.player_front_line < battle.default_player_front_line
                and battle.enemy_front_line < battle.total_lines
            ):
                battle.player_front_line += 1
                battle.enemy_front_line += 1
                battle.player_recenter_pressure = 0.0
                highlights.append("The allied lines recover ground and re-center.")

        if (
            (enemy_missing > 0 or enemy_intrusion)
            and not player_progress
            and battle.enemy_recenter_pressure >= enemy_threshold
        ):
            if battle.enemy_front_line > battle.default_enemy_front_line and battle.player_front_line >= 0:
                battle.player_front_line -= 1
                battle.enemy_front_line -= 1
                battle.enemy_recenter_pressure = 0.0
                highlights.append("The enemy lines recover ground and re-center.")

    def _check_off_map_outcome(self, battle: BattleState, highlights: list[str]) -> bool:
        if battle.enemy_front_line >= battle.total_lines:
            battle.phase = BattlePhase.RESOLVED
            battle.outcome = BattleOutcome.VICTORY
            battle.result_summary = "The enemy is pressed off the field and breaks."
            highlights.append("Enemy morale breaks as they are driven off the field.")
            battle.pending_triggers.append(BattleTrigger(BattleTriggerType.MORALE_BREAK, battle.result_summary))
            return True
        if battle.player_front_line < 0:
            battle.phase = BattlePhase.RESOLVED
            if battle.encounter.encounter_type == EncounterType.SCAVENGING:
                battle.outcome = BattleOutcome.RETREAT
                battle.result_summary = "Your force is driven off the map and forced to retreat."
                battle.pending_triggers.append(BattleTrigger(BattleTriggerType.FORCED_RETREAT, battle.result_summary))
            else:
                battle.outcome = BattleOutcome.DEFEAT
                battle.result_summary = "Your force is driven off the map and defeated in the portal battle."
                battle.pending_triggers.append(BattleTrigger(BattleTriggerType.MORALE_BREAK, battle.result_summary))
            highlights.append(battle.result_summary)
            return True
        return False

    def _handle_reinforcements(self, battle: BattleState, highlights: list[str]) -> list:
        arrivals: list = []
        due = [
            entry
            for entry in battle.encounter.reinforcements
            if int(entry.exchange_number) == int(battle.exchange_count)
        ]
        for reinforcement in due:
            for entry in reinforcement.entries:
                new_units, new_stacks = self._spawn_enemy_entry(entry)
                battle.enemy_units.extend(new_units)
                battle.enemy_stacks.extend(new_stacks)
                arrivals.extend(new_units)
                arrivals.extend(new_stacks)
            message = reinforcement.message or "Reinforcements arrive."
            highlights.append(message)
            battle.pending_triggers.append(BattleTrigger(BattleTriggerType.REINFORCEMENT, message))
        if arrivals:
            self._seed_new_entities_action_times(battle, arrivals)
        return arrivals

    def _total_health_ratio(self, active_entities: list, all_entities: list) -> float:
        current = sum(self._entity_health(entity) for entity in active_entities)
        maximum = sum(self._entity_max_health(entity) for entity in all_entities) or 1.0
        return max(0.0, min(1.0, current / maximum))
