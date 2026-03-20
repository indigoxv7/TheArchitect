from __future__ import annotations

from src.config.tuning import battle_factor
from src.domain.Character import HealthState
from src.domain.main_character import MainCharacter
from src.domain.mission import MissionObjectiveStatus
from src.domain.combat.enums import BattleOutcome, BattlePhase
from src.domain.combat.state import BattleState


class BattleMissionTrackingMixin:
    def _capture_starting_positions(self, battle: BattleState):
        for entity in list(battle.ally_units) + list(battle.enemy_units) + list(battle.enemy_stacks):
            entity.starting_line = int(getattr(entity, "line", 0) or 0)

    def _count_remaining_enemies(self, battle: BattleState) -> int:
        total = 0
        for entity in list(battle.enemy_units) + list(battle.enemy_stacks):
            total += self._entity_count(entity)
        return total

    def _count_non_player_allies_remaining(self, battle: BattleState) -> int:
        return sum(
            1 for entity in battle.ally_units if entity.alive and not bool(getattr(entity, "is_player_owned", False))
        )

    def _initialize_mission_statistics(self, battle: BattleState):
        battle.mission_statistics.totalStartingEnemies = sum(1 for entity in battle.enemy_units if entity.alive) + sum(
            max(0, int(getattr(stack, "max_count", 0) or 0)) for stack in battle.enemy_stacks
        )
        battle.mission_statistics.totalStartingAllies = sum(
            1 for entity in battle.ally_units if not bool(getattr(entity, "is_player_owned", False))
        )
        battle.mission_statistics.enemiesRemaining = self._count_remaining_enemies(battle)
        battle.mission_statistics.alliesRemaining = self._count_non_player_allies_remaining(battle)
        battle.mission_statistics.timeInsideMissionHours = float(battle.exchange_count) * battle_factor(
            "hours_per_exchange", self.HOURS_PER_EXCHANGE
        )
        self._capture_starting_positions(battle)

    def _refresh_dynamic_mission_statistics(self, battle: BattleState):
        stats = battle.mission_statistics
        stats.enemiesRemaining = self._count_remaining_enemies(battle)
        stats.alliesRemaining = self._count_non_player_allies_remaining(battle)
        stats.timeInsideMissionHours = float(battle.exchange_count) * battle_factor(
            "hours_per_exchange", self.HOURS_PER_EXCHANGE
        )
        for entity in battle.ally_units:
            if bool(getattr(entity, "is_player_owned", False)):
                continue
            unit_id = str(getattr(entity, "unit_id", "") or "")
            if not unit_id:
                continue
            stats.unitAliveStates[unit_id] = bool(entity.alive)
            stats.unitDistancesMoved[unit_id] = max(
                stats.unitDistancesMoved.get(unit_id, 0.0),
                float(abs(int(getattr(entity, "line", 0) or 0) - int(getattr(entity, "starting_line", 0) or 0))),
            )
        if stats.startingImportantObjects > 0 and stats.importantObjectsRemaining <= 0:
            stats.importantObjectsRemaining = 0

    def _refresh_mission_state(self, battle: BattleState, mission_complete: bool):
        self._refresh_dynamic_mission_statistics(battle)
        status = battle.mission_objective.evaluate(battle.mission_statistics, mission_complete=mission_complete)
        battle.mission_objective_status = status
        if battle.phase != BattlePhase.RESOLVED:
            if status == MissionObjectiveStatus.SUCCESS:
                battle.phase = BattlePhase.RESOLVED
                battle.outcome = BattleOutcome.VICTORY
                battle.result_summary = f"Mission success: {battle.mission_objective.describe()}."
            elif status == MissionObjectiveStatus.FAILURE:
                battle.phase = BattlePhase.RESOLVED
                battle.outcome = BattleOutcome.DEFEAT
                battle.result_summary = f"Mission failed: {battle.mission_objective.describe()}."
        elif status == MissionObjectiveStatus.SUCCESS and battle.outcome != BattleOutcome.DEFEAT:
            battle.outcome = BattleOutcome.VICTORY
            battle.result_summary = battle.result_summary or f"Mission success: {battle.mission_objective.describe()}."
        elif mission_complete and status == MissionObjectiveStatus.FAILURE:
            if battle.outcome != BattleOutcome.RETREAT:
                battle.outcome = BattleOutcome.DEFEAT
            battle.result_summary = f"Mission failed: {battle.mission_objective.describe()}."

    def record_units_recruited(self, battle: BattleState, count: int):
        battle.mission_statistics.unitsRecruited += max(0, int(count or 0))
        self._refresh_mission_state(battle, mission_complete=False)
        self.save_battle(battle)

    def record_resources_gathered(self, battle: BattleState, amount: int):
        battle.mission_statistics.basicResourcesGathered += max(0, int(amount or 0))
        self._refresh_mission_state(battle, mission_complete=False)
        self.save_battle(battle)

    def record_package_delivery(self, battle: BattleState, item_id: str, allegiance_id: str, count: int = 1):
        delivered_count = max(0, int(count or 0))
        if delivered_count <= 0:
            return
        stats = battle.mission_statistics
        stats.packagesDelivered += delivered_count
        composite_key = f"{str(item_id or '').strip()}|{str(allegiance_id or '').strip()}"
        stats.deliveredPackageCounts[composite_key] = (
            stats.deliveredPackageCounts.get(composite_key, 0) + delivered_count
        )
        self._refresh_mission_state(battle, mission_complete=False)
        self.save_battle(battle)

    def set_important_object_counts(self, battle: BattleState, starting_count: int, remaining_count: int | None = None):
        stats = battle.mission_statistics
        stats.startingImportantObjects = max(0, int(starting_count or 0))
        stats.importantObjectsRemaining = max(
            0, int(remaining_count if remaining_count is not None else starting_count or 0)
        )
        self._refresh_mission_state(battle, mission_complete=False)
        self.save_battle(battle)

    def record_ally_escape_progress(self, battle: BattleState, unit_id: str, distance: float, alive: bool = True):
        key = str(unit_id or "").strip()
        if not key:
            return
        battle.mission_statistics.unitDistancesMoved[key] = max(
            battle.mission_statistics.unitDistancesMoved.get(key, 0.0),
            max(0.0, float(distance or 0.0)),
        )
        battle.mission_statistics.unitAliveStates[key] = bool(alive)
        self._refresh_mission_state(battle, mission_complete=False)
        self.save_battle(battle)

    def _finalize_battle(self, battle: BattleState, record_memory: bool = True):
        self._refresh_mission_state(battle, mission_complete=True)
        player = self.player_service.get_player_sync(battle.player_id)
        if player is not None:
            for unit in battle.ally_units:
                source = self._player_source_character(battle.player_id, unit.character_instance_id)
                if source is None:
                    continue
                source.health = max(0.0, float(unit.health))
                state_name = self._normalize_health_state_name(unit.health_state)
                if battle.outcome == BattleOutcome.DEFEAT and source.health <= 0:
                    state_name = "DEAD"
                source.healthState = HealthState[state_name]
                if isinstance(source, MainCharacter):
                    source.stats.missionCount = int(getattr(source.stats, "missionCount", 0) or 0) + 1
            self.player_service.persist_player(player)
        if record_memory:
            self._append_memory_event(battle, battle.result_summary or f"Battle ends: {battle.outcome.name}.")
        self.clear_battle(battle.player_id)
