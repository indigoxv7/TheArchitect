from __future__ import annotations

import random
from typing import Any

from src.domain.combat.enums import BattleOutcome, BattlePhase, CommanderStance, TargetPriority, TokenPolicy
from src.domain.combat.state import BattleState
from src.services.battle.battle_setup import BattleRosterBuilder, BattleSetupMixin
from src.services.battle.consumables import BattleConsumablesMixin
from src.services.battle.damage_resolution import BattleDamageResolutionMixin
from src.services.battle.entity_runtime import BattleEntityRuntimeMixin
from src.services.battle.exchange_flow import BattleExchangeFlowMixin
from src.services.battle.formation import BattleFormationMixin
from src.services.battle.memory import BattleMemoryMixin
from src.services.battle.mission_tracking import BattleMissionTrackingMixin
from src.services.battle.strategy import BattleStrategyMixin
from src.services.battle.targeting import BattleTargetingMixin
from src.services.damage_calculator import DamageCalculator


class BattleService(
    BattleSetupMixin,
    BattleEntityRuntimeMixin,
    BattleMissionTrackingMixin,
    BattleTargetingMixin,
    BattleDamageResolutionMixin,
    BattleFormationMixin,
    BattleExchangeFlowMixin,
    BattleConsumablesMixin,
    BattleStrategyMixin,
    BattleMemoryMixin,
):
    HOURS_PER_EXCHANGE = 0.25
    STRATEGY_INJECTION_PATTERNS = (
        r"ignore\s+previous",
        r"system\s+prompt",
        r"developer\s+message",
        r"tool\s+call",
        r"jailbreak",
        r"assistant",
        r"chatgpt",
    )

    def __init__(
        self,
        context,
        player_service,
        item_service,
        spell_service,
        character_service,
        race_service,
        encounter_service,
        active_battle_store,
        damage_calculator: DamageCalculator | None = None,
        openai_service=None,
        memory_service=None,
        nano_reward_calculator=None,
    ):
        self.context = context
        self.player_service = player_service
        self.item_service = item_service
        self.spell_service = spell_service
        self.character_service = character_service
        self.race_service = race_service
        self.encounter_service = encounter_service
        self.store = active_battle_store
        self.damage_calculator = damage_calculator if damage_calculator is not None else DamageCalculator()
        self.openai_service = openai_service
        self.memory_service = memory_service
        self.nano_reward_calculator = nano_reward_calculator
        self.mission_runtime_service = None
        self._rng = random.Random()
        self.roster_builder = BattleRosterBuilder(
            context=context,
            item_service=item_service,
            character_service=character_service,
            health_state_for_ratio=self._health_state_for_ratio,
        )

    def set_mission_runtime_service(self, mission_runtime_service):
        self.mission_runtime_service = mission_runtime_service

    def cycle_stance(self, battle: BattleState):
        values = list(CommanderStance)
        index = values.index(battle.orders.stance)
        battle.orders.stance = values[(index + 1) % len(values)]
        battle.cached_victory_odds = None
        self.save_battle(battle)

    def cycle_target_priority(self, battle: BattleState):
        values = list(TargetPriority)
        index = values.index(battle.orders.target_priority)
        battle.orders.target_priority = values[(index + 1) % len(values)]
        battle.cached_victory_odds = None
        self.save_battle(battle)

    def cycle_token_policy(self, battle: BattleState):
        values = list(TokenPolicy)
        index = values.index(battle.orders.token_policy)
        battle.orders.token_policy = values[(index + 1) % len(values)]
        battle.cached_victory_odds = None
        self.save_battle(battle)

    def set_active_tab(self, battle: BattleState, tab_name: str):
        battle.active_tab = str(tab_name or "Orders")
        self.save_battle(battle)

    def hold_position(self, battle: BattleState):
        battle.orders.stance = CommanderStance.HOLD
        self.save_battle(battle)

    def retreat(self, battle: BattleState) -> BattleState:
        if not battle.encounter.allow_retreat:
            raise ValueError("Retreat is disabled in this encounter.")
        battle.phase = BattlePhase.RESOLVED
        battle.outcome = BattleOutcome.RETREAT
        battle.result_summary = "You order a retreat and disengage the force."
        self._finalize_battle(battle, record_memory=True)
        return battle

    def build_battle_snapshot(self, battle: BattleState) -> dict[str, Any]:
        odds = (
            self.estimate_victory_odds(battle)
            if battle.phase != BattlePhase.RESOLVED
            else (1.0 if battle.outcome == BattleOutcome.VICTORY else 0.0)
        )
        recent_summary = battle.recent_summaries[-1] if battle.recent_summaries else None
        return {
            "encounter_name": battle.encounter.name,
            "mission_name": battle.mission_name or battle.encounter.name,
            "terrain": battle.encounter.terrain,
            "exchange": battle.exchange_count,
            "stance": battle.orders.stance.name,
            "width": battle.width,
            "total_lines": battle.total_lines,
            "player_front_line": battle.player_front_line,
            "enemy_front_line": battle.enemy_front_line,
            "phase": battle.phase.name,
            "outcome": battle.outcome.name,
            "objective": battle.encounter.objective_text,
            "objective_description": battle.mission_objective.describe(),
            "objective_status": battle.mission_objective_status.value,
            "allow_retreat": battle.encounter.allow_retreat,
            "cached_victory_odds": odds,
            "mission_statistics": battle.mission_statistics.to_dict(),
            "recent_highlights": recent_summary.highlights if recent_summary else [],
            "recent_triggers": [trigger.message for trigger in (recent_summary.triggers if recent_summary else [])],
            "allies": [
                {
                    "name": unit.name,
                    "health": round(unit.health, 1),
                    "max_health": round(unit.max_health, 1),
                    "state": unit.health_state,
                    "line": unit.line,
                    "lane": unit.lane_start,
                    "role": unit.role.name,
                }
                for unit in battle.ally_units
            ],
            "enemies": [
                {
                    "name": unit.name,
                    "health": round(self._entity_health(unit), 1),
                    "max_health": round(self._entity_max_health(unit), 1),
                    "state": unit.health_state,
                    "line": unit.line,
                    "lane": unit.lane_start,
                    "role": unit.role.name,
                    "count": getattr(unit, "current_count", 1),
                }
                for unit in list(battle.enemy_units) + list(battle.enemy_stacks)
            ],
        }
