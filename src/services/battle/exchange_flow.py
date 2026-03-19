from __future__ import annotations

import random

from src.config.tuning import battle_factor
from src.domain.combat.enums import (
    BattleOutcome,
    BattlePhase,
    BattleTeam,
    BattleTriggerType,
    CommanderStance,
    EncounterType,
)
from src.domain.combat.state import BattleExchangeSummary, BattleState, BattleTrigger, CommanderOrders
from src.domain.combat_timing import (
    ExertionLevel,
    can_take_offensive_action,
    exchange_duration_seconds,
    schedule_next_action,
    spend_stamina,
    sync_stamina,
)


class BattleExchangeFlowMixin:
    def _timeline_needs_seeding(self, battle: BattleState) -> bool:
        active_entities = self._active_entities(battle)
        return bool(active_entities) and all(
            float(getattr(entity, "next_action_time", 0.0) or 0.0) == 0.0 for entity in active_entities
        )

    def _execute_actor_turn(self, battle: BattleState, attacker, highlights: list[str]):
        if self._entity_health(attacker) <= 0.0:
            return
        current_time = battle.battle_time_seconds
        self._ensure_entity_runtime(attacker, current_time)
        sync_stamina(attacker, current_time)
        if not can_take_offensive_action(getattr(attacker, "exertion_level", ExertionLevel.FRESH.name)):
            highlights.append(f"{self._entity_name(attacker)} is exhausted and cannot press the attack.")
            schedule_next_action(attacker, self._entity_speed(attacker), current_time)
            return

        defenders = (
            self._active_enemies(battle)
            if getattr(attacker, "team", BattleTeam.ALLY) == BattleTeam.ALLY
            else self._active_allies(battle)
        )
        orders = battle.orders if getattr(attacker, "team", BattleTeam.ALLY) == BattleTeam.ALLY else None
        live_defenders = [entity for entity in defenders if self._entity_health(entity) > 0.0]
        action_attempted = False
        attack_count = self._entity_attack_count(attacker)
        for _ in range(attack_count):
            if not live_defenders:
                break
            target = self._select_target(battle, attacker, live_defenders, orders)
            if target is None:
                break
            action_attempted = (
                self._resolve_attack(
                    battle,
                    attacker,
                    target,
                    orders,
                    highlights,
                    current_time=current_time,
                )
                or action_attempted
            )
            live_defenders = [entity for entity in defenders if self._entity_health(entity) > 0.0]
        if action_attempted:
            spend_stamina(attacker, self._offensive_action_cost(battle, attacker), current_time)
        schedule_next_action(attacker, self._entity_speed(attacker), current_time)

    def _resolve_team_attacks(
        self,
        battle: BattleState,
        attackers: list,
        defenders: list,
        orders: CommanderOrders | None,
        highlights: list[str],
    ):
        for attacker in attackers:
            if self._entity_health(attacker) <= 0.0:
                continue
            attack_count = self._entity_attack_count(attacker)
            live_defenders = [entity for entity in defenders if self._entity_health(entity) > 0.0]
            for _ in range(attack_count):
                if not live_defenders:
                    return
                target = self._select_target(battle, attacker, live_defenders, orders)
                if target is None:
                    break
                self._resolve_attack(battle, attacker, target, orders, highlights)
                live_defenders = [entity for entity in defenders if self._entity_health(entity) > 0.0]

    def resolve_exchange(
        self, battle: BattleState, persist: bool = True, record_memory: bool = True
    ) -> BattleExchangeSummary:
        if battle.phase == BattlePhase.RESOLVED:
            return (
                battle.recent_summaries[-1]
                if battle.recent_summaries
                else BattleExchangeSummary(exchange_number=battle.exchange_count)
            )

        battle.phase = BattlePhase.ACTIVE
        battle.exchange_count += 1
        highlights: list[str] = []
        triggers: list[BattleTrigger] = []
        exchange_start_time = float(battle.battle_time_seconds)
        exchange_end_time = exchange_start_time + exchange_duration_seconds()
        self._handle_reinforcements(battle, highlights)
        if self._timeline_needs_seeding(battle):
            self._seed_initial_action_times(battle)
        self._solve_formations(battle)

        while True:
            allies = self._active_allies(battle)
            enemies = self._active_enemies(battle)
            if not allies or not enemies:
                break
            actor = self._select_next_actor(battle)
            if actor is None:
                break
            raw_actor_time = getattr(actor, "next_action_time", exchange_end_time)
            actor_time = exchange_end_time if raw_actor_time is None else float(raw_actor_time)
            if actor_time > exchange_end_time:
                break
            battle.battle_time_seconds = actor_time
            self._execute_actor_turn(battle, actor, highlights)

        battle.battle_time_seconds = exchange_end_time

        allies = self._active_allies(battle)
        enemies = self._active_enemies(battle)
        if not enemies:
            battle.phase = BattlePhase.RESOLVED
            battle.outcome = BattleOutcome.VICTORY
            battle.result_summary = "The enemy force is destroyed."
        elif not allies:
            battle.phase = BattlePhase.RESOLVED
            battle.outcome = (
                BattleOutcome.RETREAT
                if battle.encounter.encounter_type == EncounterType.SCAVENGING
                else BattleOutcome.DEFEAT
            )
            battle.result_summary = "Your force collapses under enemy pressure."
        else:
            ally_strength = self._team_strength_on_front(allies, battle.player_front_line)
            enemy_strength = self._team_strength_on_front(enemies, battle.enemy_front_line)
            progress_multiplier = battle_factor("line_progress_advantage_multiplier", 1.25)
            player_progress = ally_strength > (enemy_strength * progress_multiplier)
            enemy_progress = enemy_strength > (ally_strength * progress_multiplier)
            if battle.orders.stance == CommanderStance.ADVANCE:
                player_progress = player_progress or ally_strength > enemy_strength
            if battle.orders.stance == CommanderStance.DEFENSIVE:
                enemy_progress = enemy_progress and (
                    enemy_strength > ally_strength * battle_factor("defensive_line_hold_multiplier", 1.4)
                )

            if player_progress and not enemy_progress:
                self._advance_front(battle, BattleTeam.ALLY, highlights)
                triggers.append(BattleTrigger(BattleTriggerType.LANE_BREAK, "Allied pressure opens the line."))
            elif enemy_progress and not player_progress:
                self._advance_front(battle, BattleTeam.ENEMY, highlights)
                triggers.append(BattleTrigger(BattleTriggerType.LANE_BREAK, "Enemy pressure caves in the line."))

            if not self._check_off_map_outcome(battle, highlights):
                self._apply_recentering(battle, player_progress, enemy_progress, highlights)
                self._solve_formations(battle)

        self._refresh_mission_state(battle, mission_complete=(battle.phase == BattlePhase.RESOLVED))

        for unit in battle.ally_units:
            if unit.notable and unit.health_state in {"UNCONSCIOUS", "DEAD"}:
                triggers.append(
                    BattleTrigger(BattleTriggerType.HERO_DOWN, f"{unit.name} is {unit.health_state.lower()}.")
                )
        if battle.encounter.allow_retreat and battle.outcome == BattleOutcome.ONGOING:
            ally_hp_ratio = self._total_health_ratio(self._active_allies(battle), battle.ally_units)
            if ally_hp_ratio <= battle_factor("retreat_opportunity_health_ratio_threshold", 0.35):
                triggers.append(
                    BattleTrigger(
                        BattleTriggerType.RETREAT_OPPORTUNITY, "Retreat is available if you want to preserve the team."
                    )
                )

        summary = BattleExchangeSummary(
            exchange_number=battle.exchange_count,
            highlights=highlights[-12:],
            triggers=triggers,
            player_front_line=battle.player_front_line,
            enemy_front_line=battle.enemy_front_line,
            player_hp_ratio=self._total_health_ratio(self._active_allies(battle), battle.ally_units),
            enemy_hp_ratio=self._total_health_ratio(
                self._active_enemies(battle), battle.enemy_units + battle.enemy_stacks
            ),
        )
        battle.recent_summaries.append(summary)
        battle.recent_summaries = battle.recent_summaries[-8:]
        battle.pending_triggers = triggers
        battle.cached_victory_odds = None
        battle.cached_orders_signature = ""

        if record_memory:
            self._append_memory_event(battle, f"Exchange {battle.exchange_count}: {' '.join(summary.highlights[:3])}")

        if battle.phase == BattlePhase.RESOLVED and persist:
            self._finalize_battle(battle, record_memory=record_memory)
        elif persist:
            self.save_battle(battle)
        return summary

    def auto_resolve(self, battle: BattleState, max_exchanges: int = 24, persist: bool = True) -> BattleState:
        while battle.phase != BattlePhase.RESOLVED and battle.exchange_count < max_exchanges:
            self.resolve_exchange(battle, persist=False, record_memory=False)
        if battle.phase != BattlePhase.RESOLVED:
            battle.phase = BattlePhase.RESOLVED
            battle.outcome = BattleOutcome.RETREAT if battle.encounter.allow_retreat else BattleOutcome.DEFEAT
            battle.result_summary = "The battle times out into a withdrawal."
        if persist:
            self._finalize_battle(battle, record_memory=True)
        return battle

    def estimate_victory_odds(self, battle: BattleState, simulations: int = 32) -> float:
        signature = battle.orders.signature()
        if battle.cached_victory_odds is not None and battle.cached_orders_signature == signature:
            return float(battle.cached_victory_odds)
        wins = 0
        for index in range(max(1, int(simulations))):
            clone = BattleState.from_dict(battle.to_dict())
            clone.phase = BattlePhase.ACTIVE
            local_rng = random.Random(1000 + index)
            original_rng = self.damage_calculator._rng
            self.damage_calculator._rng = local_rng
            try:
                self.auto_resolve(clone, max_exchanges=18, persist=False)
            finally:
                self.damage_calculator._rng = original_rng
            if clone.outcome == BattleOutcome.VICTORY:
                wins += 1
        odds = wins / max(1, int(simulations))
        battle.cached_victory_odds = odds
        battle.cached_orders_signature = signature
        self.save_battle(battle)
        return odds
