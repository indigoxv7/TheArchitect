from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any

from src.config.tuning import battle_factor, character_stat_factor, misc_factor
from src.domain.character import Character, HealthState
from src.domain.character_util import ConsumableKind, HitLocation, PowerType
from src.domain.items import Consumable, Weapon
from src.domain.spells import Spell
from src.domain.character_io import character_from_state
from src.domain.combat_timing import (
    CombatRuntimeState,
    accuracy_bonus_for_exertion,
    baseline_turn_seconds,
    can_take_offensive_action,
    damage_multiplier_for_exertion,
    default_offensive_action_stamina_cost,
    defense_stat_penalty_for_exertion,
    schedule_next_action,
    spend_stamina,
    stamina_damage_from_hit,
    sync_stamina,
)
from src.services.combat_duel_shared import (
    build_runtime_state,
    character_speed,
    character_stamina_limit,
    character_stamina_regen,
    health_state_for_character,
    initialize_duel_timeline,
    max_duel_battle_time,
    parse_numeric_value,
    roll_hit_location,
    round_number_for_time,
    scaled_weapon_for_damage_multiplier,
    select_next_duel_side,
)
from src.services.combat_loadout_service import select_active_character_weapon
from src.services.damage_calculator import DamageCalculator


@dataclass
class CombatSimulationSummary:
    leftName: str
    rightName: str
    sampleCount: int
    leftWins: int
    rightWins: int
    draws: int
    leftWinRate: float
    rightWinRate: float
    averageRounds: float


@dataclass
class CombatSimulationSession:
    left_source_state: dict[str, Any]
    right_source_state: dict[str, Any]
    left_character: Character
    right_character: Character
    rng: random.Random
    debug: bool = False
    seed: int = 0
    round_number: int = 0
    next_action_times: dict[str, float] = field(default_factory=dict)
    runtime_states: dict[str, CombatRuntimeState] = field(default_factory=dict)
    tie_break_order: list[str] = field(default_factory=list)
    log_lines: list[str] = field(default_factory=list)
    finished: bool = False
    result_text: str = ""
    battle_time_seconds: float = 0.0


@dataclass
class TurnOutcome:
    lines: list[str]
    action_cost: float = 0.0
    target_stamina_before: float | None = None
    target_stamina_after: float | None = None


class CombatSimulatorService:
    MAX_DUEL_ROUNDS = 30
    DEFAULT_SEED = 20260317

    def __init__(
        self,
        character_service,
        item_service,
        spell_service,
        race_service=None,
        damage_calculator: DamageCalculator | None = None,
        seed: int = DEFAULT_SEED,
    ):
        self.character_service = character_service
        self.item_service = item_service
        self.spell_service = spell_service
        self.race_service = race_service
        self.damage_calculator = damage_calculator if damage_calculator is not None else DamageCalculator()
        self.seed = int(seed)

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @classmethod
    def _parse_numeric_value(cls, value: Any, default: float = 0.0) -> float:
        return parse_numeric_value(value, default=default)

    @staticmethod
    def _normalize_affinity_fraction(value: Any) -> float:
        try:
            numeric = float(value)
        except Exception:
            numeric = misc_factor("neutral_affinity", 0.5)
        if numeric > 1.0:
            numeric /= 100.0
        return max(0.0, min(1.0, numeric))

    @classmethod
    def _affinity_multiplier(cls, value: Any) -> float:
        fraction = cls._normalize_affinity_fraction(value)
        return misc_factor("affinity_power_min_multiplier", 0.8) + (fraction * misc_factor("affinity_power_bonus_range", 0.4))

    def _race_lookup(self, race_id: str):
        if self.race_service is None:
            return None
        return self.race_service.get_race(race_id)

    def build_character_from_state(self, state: dict[str, Any]) -> Character:
        character = character_from_state(
            copy.deepcopy(state),
            item_resolver=self.item_service.get_item,
            error_item=self.item_service.context.error_item,
        )
        character = copy.deepcopy(character)
        if hasattr(character, "EnsureRuntimeDefaults"):
            character.EnsureRuntimeDefaults()
        character.CalculateBonus()
        if hasattr(character, "ClampHealthToMax"):
            character.ClampHealthToMax()
        if hasattr(character, "RefreshHealthState"):
            character.RefreshHealthState()
        return character

    def _prepare_characters(self, left_state: dict[str, Any], right_state: dict[str, Any]) -> tuple[Character, Character]:
        left = self.build_character_from_state(left_state)
        right = self.build_character_from_state(right_state)
        left_name = str(getattr(left, "name", "Combatant") or "Combatant").strip() or "Combatant"
        right_name = str(getattr(right, "name", "Combatant") or "Combatant").strip() or "Combatant"
        if left_name.lower() == right_name.lower():
            left.name = f"{left_name}1"
            right.name = f"{right_name}2"
        return left, right

    def start_session(self, left_state: dict[str, Any], right_state: dict[str, Any], debug: bool = False, seed: int | None = None) -> CombatSimulationSession:
        actual_seed = self.seed if seed is None else int(seed)
        left, right = self._prepare_characters(left_state, right_state)
        session = CombatSimulationSession(
            left_source_state=copy.deepcopy(left_state),
            right_source_state=copy.deepcopy(right_state),
            left_character=left,
            right_character=right,
            rng=random.Random(actual_seed),
            debug=bool(debug),
            seed=actual_seed,
        )
        session.runtime_states = {
            "left": self._build_runtime_state(left),
            "right": self._build_runtime_state(right),
        }
        session.log_lines.append(f"Simulation ready: {left.name} vs {right.name}.")
        return session

    def reset_session(self, session: CombatSimulationSession) -> CombatSimulationSession:
        return self.start_session(
            left_state=session.left_source_state,
            right_state=session.right_source_state,
            debug=session.debug,
            seed=session.seed,
        )

    def run_auto(self, left_state: dict[str, Any], right_state: dict[str, Any], repeats: int = 300) -> CombatSimulationSummary:
        sample_count = max(1, int(repeats or 1))
        left_wins = 0
        right_wins = 0
        draws = 0
        total_rounds = 0
        preview = self.start_session(left_state, right_state, debug=False, seed=self.seed)
        left_name = preview.left_character.name
        right_name = preview.right_character.name
        for index in range(sample_count):
            session = self.start_session(left_state, right_state, debug=False, seed=self.seed + (index * 7919))
            rounds = self._run_to_completion(session)
            total_rounds += rounds
            if session.left_character.health > 0 and session.right_character.health <= 0:
                left_wins += 1
            elif session.right_character.health > 0 and session.left_character.health <= 0:
                right_wins += 1
            else:
                draws += 1
        return CombatSimulationSummary(
            leftName=left_name,
            rightName=right_name,
            sampleCount=sample_count,
            leftWins=left_wins,
            rightWins=right_wins,
            draws=draws,
            leftWinRate=left_wins / float(sample_count),
            rightWinRate=right_wins / float(sample_count),
            averageRounds=total_rounds / float(sample_count),
        )

    def _run_to_completion(self, session: CombatSimulationSession) -> int:
        while not session.finished:
            self.step_session(session)
        return max(0, int(session.round_number))

    @staticmethod
    def _character_speed(character: Character) -> float:
        return character_speed(character)

    @classmethod
    def _action_interval(cls, character: Character) -> float:
        return baseline_turn_seconds() / cls._character_speed(character)

    @staticmethod
    def _character_stamina_limit(character: Character) -> float:
        return character_stamina_limit(character)

    @staticmethod
    def _character_stamina_regen(character: Character) -> float:
        return character_stamina_regen(character)

    def _max_duel_battle_time(self) -> float:
        return max_duel_battle_time(self.MAX_DUEL_ROUNDS)

    def _build_runtime_state(self, character: Character) -> CombatRuntimeState:
        return build_runtime_state(character)

    @staticmethod
    def _alive_sides(session: CombatSimulationSession) -> list[str]:
        alive = []
        if float(getattr(session.left_character, "health", 0.0) or 0.0) > 0.0:
            alive.append("left")
        if float(getattr(session.right_character, "health", 0.0) or 0.0) > 0.0:
            alive.append("right")
        return alive

    def _select_next_side(self, session: CombatSimulationSession) -> str | None:
        return select_next_duel_side(self._alive_sides(session), session.next_action_times, session.tie_break_order)

    def _initialize_turn_timeline(self, session: CombatSimulationSession) -> list[str]:
        timeline = initialize_duel_timeline(session.rng)
        session.runtime_states[timeline.first_side].next_action_time = 0.0
        session.runtime_states[timeline.second_side].next_action_time = timeline.turn_gap
        session.next_action_times = dict(timeline.next_action_times)
        session.tie_break_order = list(timeline.tie_break_order)
        session.round_number = 1
        session.battle_time_seconds = 0.0
        lead_name = session.left_character.name if timeline.first_side == "left" else session.right_character.name
        round_line = f"Round 1 begins. Lead action: {lead_name}."
        lines = [round_line]
        session.log_lines.append(round_line)
        if session.debug:
            lines.append(
                "  Debug: "
                f"lead={timeline.first_side}; "
                f"turn gap={timeline.turn_gap:.2f}s; "
                f"left speed={self._character_speed(session.left_character):.2f}, "
                f"right speed={self._character_speed(session.right_character):.2f}."
            )
            session.log_lines.append(lines[-1])
        return lines

    def step_session(self, session: CombatSimulationSession) -> list[str]:
        if session.finished:
            return []

        if not session.next_action_times:
            new_lines = self._initialize_turn_timeline(session)
        else:
            new_lines = []

        side = self._select_next_side(session)
        if side is None:
            session.finished = True
            session.result_text = "Both combatants fall."
            session.log_lines.append(session.result_text)
            return new_lines + [session.result_text]
        turn_start_time = float(session.next_action_times.get(side, 0.0))
        if turn_start_time > self._max_duel_battle_time():
            session.finished = True
            session.result_text = "Simulation ends in a draw."
            session.log_lines.append(session.result_text)
            return new_lines + [session.result_text]

        round_number = round_number_for_time(turn_start_time)
        if round_number > session.round_number:
            session.round_number = round_number
            lead_name = session.left_character.name if side == "left" else session.right_character.name
            round_line = f"Round {session.round_number} begins. Lead action: {lead_name}."
            session.log_lines.append(round_line)
            new_lines.append(round_line)

        session.battle_time_seconds = turn_start_time
        attacker = session.left_character if side == "left" else session.right_character
        defender = session.right_character if side == "left" else session.left_character

        if attacker.health <= 0 or defender.health <= 0:
            return new_lines

        attacker_runtime = session.runtime_states[side]
        defender_runtime = session.runtime_states["right" if side == "left" else "left"]
        attacker_stamina_before = sync_stamina(attacker_runtime, turn_start_time)
        attacker_exertion_before = str(attacker_runtime.exertion_level)
        sync_stamina(defender_runtime, turn_start_time)
        outcome = self._take_turn(attacker, defender, session, side)

        if outcome.action_cost > 0.0:
            spend_stamina(attacker_runtime, outcome.action_cost, turn_start_time)
        attacker_stamina_after = float(attacker_runtime.stamina_current)
        attacker_exertion_after = str(attacker_runtime.exertion_level)
        session.next_action_times[side] = schedule_next_action(attacker_runtime, self._character_speed(attacker), turn_start_time)
        session.runtime_states[side].next_action_time = session.next_action_times[side]
        session.tie_break_order = [entry for entry in session.tie_break_order if entry != side] + [side]
        action_lines = list(outcome.lines)
        if session.debug:
            runtime_line = (
                "  Debug: "
                f"time={turn_start_time:.2f}s; "
                f"stamina {attacker_stamina_before:.2f}->{attacker_stamina_after:.2f}; "
                f"exertion {attacker_exertion_before}->{attacker_exertion_after}; "
                f"action cost={outcome.action_cost:.2f}; "
                f"next action={session.next_action_times[side]:.2f}s."
            )
            if outcome.target_stamina_before is not None and outcome.target_stamina_after is not None:
                runtime_line = (
                    runtime_line[:-1]
                    + f" Target stamina {outcome.target_stamina_before:.2f}->{outcome.target_stamina_after:.2f}."
                )
            action_lines.append(runtime_line)
        session.log_lines.extend(action_lines)
        new_lines.extend(action_lines)

        if defender.health <= 0:
            session.finished = True
            session.result_text = f"{attacker.name} wins."
            session.log_lines.append(session.result_text)
            new_lines.append(session.result_text)
        elif session.left_character.health <= 0 and session.right_character.health <= 0:
            session.finished = True
            session.result_text = "Both combatants fall."
            session.log_lines.append(session.result_text)
            new_lines.append(session.result_text)
        return new_lines

    def _take_turn(self, attacker: Character, defender: Character, session: CombatSimulationSession, side: str) -> TurnOutcome:
        attacker_runtime = session.runtime_states[side]
        defender_runtime = session.runtime_states["right" if side == "left" else "left"]
        turn_start_time = session.battle_time_seconds
        if not can_take_offensive_action(attacker_runtime.exertion_level):
            return TurnOutcome(
                lines=[f"{attacker.name} is exhausted and cannot act offensively."],
                action_cost=0.0,
            )

        consumable = self._select_consumable(attacker, defender, session.round_number)
        if consumable is not None:
            return self._resolve_consumable_turn(attacker, defender, consumable, session)

        weapon = self._active_weapon(attacker)
        spell = self._best_spell(attacker)
        spell_power = self._adjusted_spell_power(attacker, spell)
        weapon_ceiling = float(getattr(weapon, "damageMax", getattr(weapon, "damageMin", 0.0)) or 0.0) if weapon is not None else 0.0
        if spell is not None and spell_power >= max(weapon_ceiling, 0.1):
            return self._resolve_spell_turn(attacker, defender, spell, session, attacker_runtime, defender_runtime, turn_start_time)
        return self._resolve_weapon_turn(attacker, defender, weapon or self._default_unarmed_weapon(), session, attacker_runtime, defender_runtime, turn_start_time)

    def _select_consumable(self, attacker: Character, defender: Character, round_number: int) -> Consumable | None:
        gear = getattr(attacker, "gear", None)
        inventory = list(getattr(gear, "inventory", []) or []) if gear is not None else []
        if not inventory:
            return None
        max_health = max(1.0, float(getattr(attacker, "GetMaxHealth", lambda: 100.0)()))
        health_ratio = float(getattr(attacker, "health", 0.0) or 0.0) / max_health
        for item in inventory:
            if not isinstance(item, Consumable):
                continue
            if (item.isOffensive or item.consumableKind == ConsumableKind.BOMB) and round_number <= battle_factor("combat_sim_offensive_consumable_round_limit", 1):
                return item
            if health_ratio <= battle_factor("combat_sim_supportive_consumable_health_ratio_threshold", 0.6) and not item.isOffensive:
                return item
        return None

    def _consume_item(self, character: Character, item: Consumable):
        gear = getattr(character, "gear", None)
        if gear is None:
            return
        inventory = list(getattr(gear, "inventory", []) or [])
        for index, entry in enumerate(inventory):
            if entry is item:
                inventory.pop(index)
                gear.inventory = inventory
                return
        for index, entry in enumerate(inventory):
            if str(getattr(entry, "itemId", "") or "") == str(getattr(item, "itemId", "") or ""):
                inventory.pop(index)
                gear.inventory = inventory
                return

    def _active_weapon(self, character: Character) -> Weapon | None:
        return select_active_character_weapon(character, race_lookup=self._race_lookup)

    def _best_spell(self, character: Character) -> Spell | None:
        best_spell = None
        best_power = 0.0
        for spell in getattr(character, "spells", []) or []:
            adjusted = self._adjusted_spell_power(character, spell)
            if adjusted > best_power:
                best_power = adjusted
                best_spell = spell
        return best_spell

    def _adjusted_spell_power(self, character: Character, spell: Spell | None) -> float:
        if spell is None:
            return 0.0
        base_power = max(
            self._parse_numeric_value(getattr(spell, "power", 0.0), 0.0),
            float(getattr(spell, "powerLevel", 0.0) or 0.0),
        )
        affinity_name = str(getattr(getattr(spell, "affinity", None), "name", getattr(spell, "affinity", "MANA")) or "MANA").lower()
        affinities = getattr(character, "finalAffinities", None) or getattr(character, "affinities", None)
        neutral_affinity = misc_factor("neutral_affinity", 0.5)
        affinity_value = getattr(affinities, affinity_name, neutral_affinity) if affinities is not None else neutral_affinity
        return max(0.0, base_power * self._affinity_multiplier(affinity_value))

    def _resolve_weapon_turn(
        self,
        attacker: Character,
        defender: Character,
        weapon: Weapon,
        session: CombatSimulationSession,
        attacker_runtime: CombatRuntimeState,
        defender_runtime: CombatRuntimeState,
        turn_start_time: float,
    ) -> TurnOutcome:
        calculator = DamageCalculator(rng=session.rng)
        attacker_stat = float(getattr(attacker.finalAttributes, "physicalPower", 5.0))
        defender_stat = max(
            0.0,
            float(getattr(defender.finalAttributes, "physicalResistance", 5.0))
            - defense_stat_penalty_for_exertion(defender_runtime.exertion_level),
        )
        hit_chance = calculator.calculate_hit_chance(
            attacker_stat,
            defender_stat,
            bonus=accuracy_bonus_for_exertion(attacker_runtime.exertion_level),
        )
        hit_roll = session.rng.random()
        did_hit = hit_roll <= hit_chance
        lines: list[str] = []
        if not did_hit:
            lines.append(f"{attacker.name} attacks {defender.name} with {weapon.name}, but misses.")
            if session.debug:
                lines.append(
                    f"  Debug: hit roll={hit_roll:.4f}, needed<={hit_chance:.4f}; attacker stat={attacker_stat:.2f}, defender stat={defender_stat:.2f}."
                )
            return TurnOutcome(lines=lines, action_cost=max(0.0, float(getattr(weapon, "staminaCost", default_offensive_action_stamina_cost()) or default_offensive_action_stamina_cost())))

        location = self._roll_hit_location(session.rng)
        scaled_weapon = self._scaled_weapon_for_damage_multiplier(
            weapon,
            damage_multiplier_for_exertion(attacker_runtime.exertion_level),
        )
        result = calculator.calculate_physical_hit_to_location(
            attacker=attacker,
            defender=defender,
            weapon=scaled_weapon,
            location=location,
            applyArmorDamageToGear=True,
        )
        damage = max(0.0, result.hpFinal)
        target_stamina_before = None
        target_stamina_after = None
        defender.health = max(0.0, float(defender.health) - damage)
        defender.healthState = self._health_state(defender)
        if damage > 0.0:
            lines.append(f"{attacker.name} hits {defender.name} with {weapon.name} in the {location.name.lower()} for {damage:.1f} damage.")
            target_stamina_before = float(defender_runtime.stamina_current)
            target_stamina_after = spend_stamina(defender_runtime, stamina_damage_from_hit(damage), turn_start_time)
        else:
            lines.append(f"{attacker.name} lands {weapon.name} on {defender.name}, but fails to injure them.")
        if session.debug:
            scaled_armor_roll = result.rollArmor * result.powerMultiplier
            scaled_hp_roll = result.rollHp * result.powerMultiplier
            lines.append(
                "  Debug: "
                f"hit roll={hit_roll:.4f} <= {hit_chance:.4f}; "
                f"base armor roll={result.rollArmor:.2f}, base hp roll={result.rollHp:.2f}, "
                f"power x={result.powerMultiplier:.3f}, scaled armor={scaled_armor_roll:.2f}, scaled hp={scaled_hp_roll:.2f}, "
                f"armor {result.armorBefore:.2f}->{result.armorAfter:.2f} (dmg {result.armorDamage:.2f}), "
                f"hp after armor={result.hpPreResistance:.2f}, penetration={result.penetration:.2f}, "
                f"resist eff={result.penetrationEffectiveness:.3f}, final hp={result.hpFinal:.2f}."
            )
        return TurnOutcome(
            lines=lines,
            action_cost=max(0.0, float(getattr(weapon, "staminaCost", default_offensive_action_stamina_cost()) or default_offensive_action_stamina_cost())),
            target_stamina_before=target_stamina_before,
            target_stamina_after=target_stamina_after,
        )

    def _resolve_spell_turn(
        self,
        attacker: Character,
        defender: Character,
        spell: Spell,
        session: CombatSimulationSession,
        attacker_runtime: CombatRuntimeState,
        defender_runtime: CombatRuntimeState,
        turn_start_time: float,
    ) -> TurnOutcome:
        calculator = DamageCalculator(rng=session.rng)
        attacker_stat = float(getattr(attacker.finalAttributes, "magicPower", 5.0))
        defender_stat = max(
            0.0,
            float(getattr(defender.finalAttributes, "magicResistance", 5.0))
            - defense_stat_penalty_for_exertion(defender_runtime.exertion_level),
        )
        hit_chance = calculator.calculate_hit_chance(
            attacker_stat,
            defender_stat,
            bonus=accuracy_bonus_for_exertion(attacker_runtime.exertion_level),
        )
        hit_roll = session.rng.random()
        did_hit = hit_roll <= hit_chance
        spell_power = self._adjusted_spell_power(attacker, spell) * damage_multiplier_for_exertion(attacker_runtime.exertion_level)
        result = calculator.calculate_magic_hit(
            attacker=attacker,
            defender=defender,
            spell_power=spell_power,
            hit_chance=hit_chance,
            did_hit=did_hit,
        )
        damage = max(0.0, result.hpFinal)
        target_stamina_before = None
        target_stamina_after = None
        if damage > 0.0:
            defender.health = max(0.0, float(defender.health) - damage)
            defender.healthState = self._health_state(defender)
            lines = [f"{attacker.name} casts {spell.name} on {defender.name} for {damage:.1f} damage."]
            target_stamina_before = float(defender_runtime.stamina_current)
            target_stamina_after = spend_stamina(defender_runtime, stamina_damage_from_hit(damage), turn_start_time)
        else:
            lines = [f"{attacker.name} casts {spell.name}, but misses {defender.name}."]
        if session.debug:
            lines.append(
                "  Debug: "
                f"hit roll={hit_roll:.4f}, needed<={hit_chance:.4f}; "
                f"base power={result.basePower:.2f}, power x={result.powerMultiplier:.3f}, "
                f"resistance x={result.resistanceMultiplier:.3f}, final hp={result.hpFinal:.2f}."
            )
        return TurnOutcome(
            lines=lines,
            action_cost=default_offensive_action_stamina_cost(),
            target_stamina_before=target_stamina_before,
            target_stamina_after=target_stamina_after,
        )

    def _resolve_consumable_turn(
        self,
        attacker: Character,
        defender: Character,
        item: Consumable,
        session: CombatSimulationSession,
    ) -> TurnOutcome:
        self._consume_item(attacker, item)
        if item.isOffensive or item.consumableKind == ConsumableKind.BOMB:
            attacker_runtime = session.runtime_states["left" if attacker is session.left_character else "right"]
            defender_runtime = session.runtime_states["right" if attacker is session.left_character else "left"]
            return self._resolve_offensive_consumable(
                attacker,
                defender,
                item,
                session,
                attacker_runtime,
                defender_runtime,
                session.battle_time_seconds,
            )
        healing = self._consumable_healing(attacker, item)
        before = float(getattr(attacker, "health", 0.0) or 0.0)
        max_health = max(1.0, float(getattr(attacker, "GetMaxHealth", lambda: 100.0)()))
        attacker.health = min(max_health, before + healing)
        attacker.healthState = self._health_state(attacker)
        lines = [f"{attacker.name} uses {item.name} and restores {attacker.health - before:.1f} health."]
        if session.debug:
            lines.append(f"  Debug: heal amount={healing:.2f}, health {before:.1f}->{attacker.health:.1f}.")
        return TurnOutcome(lines=lines, action_cost=0.0)

    def _resolve_offensive_consumable(
        self,
        attacker: Character,
        defender: Character,
        item: Consumable,
        session: CombatSimulationSession,
        attacker_runtime: CombatRuntimeState,
        defender_runtime: CombatRuntimeState,
        turn_start_time: float,
    ) -> TurnOutcome:
        calculator = DamageCalculator(rng=session.rng)
        attacker_stat = float(getattr(attacker.finalAttributes, "magicPower", 5.0))
        defender_stat = max(
            0.0,
            float(getattr(defender.finalAttributes, "magicResistance", 5.0))
            - defense_stat_penalty_for_exertion(defender_runtime.exertion_level),
        )
        hit_chance = calculator.calculate_hit_chance(
            attacker_stat,
            defender_stat,
            bonus=accuracy_bonus_for_exertion(attacker_runtime.exertion_level),
        )
        hit_roll = session.rng.random()
        did_hit = hit_roll <= hit_chance
        spell_power = self._consumable_damage_power(attacker, item) * damage_multiplier_for_exertion(attacker_runtime.exertion_level)
        result = calculator.calculate_magic_hit(
            attacker=attacker,
            defender=defender,
            spell_power=spell_power,
            hit_chance=hit_chance,
            did_hit=did_hit,
        )
        damage = max(0.0, result.hpFinal)
        target_stamina_before = None
        target_stamina_after = None
        if damage > 0.0:
            defender.health = max(0.0, float(defender.health) - damage)
            defender.healthState = self._health_state(defender)
            lines = [f"{attacker.name} uses {item.name} on {defender.name} for {damage:.1f} damage."]
            target_stamina_before = float(defender_runtime.stamina_current)
            target_stamina_after = spend_stamina(defender_runtime, stamina_damage_from_hit(damage), turn_start_time)
        else:
            lines = [f"{attacker.name} uses {item.name}, but fails to affect {defender.name}."]
        if session.debug:
            lines.append(
                "  Debug: "
                f"hit roll={hit_roll:.4f}, needed<={hit_chance:.4f}; "
                f"base power={result.basePower:.2f}, power x={result.powerMultiplier:.3f}, "
                f"resistance x={result.resistanceMultiplier:.3f}, final hp={result.hpFinal:.2f}."
            )
        return TurnOutcome(
            lines=lines,
            action_cost=default_offensive_action_stamina_cost(),
            target_stamina_before=target_stamina_before,
            target_stamina_after=target_stamina_after,
        )

    @staticmethod
    def _scaled_weapon_for_damage_multiplier(weapon: Weapon, damage_multiplier: float) -> Weapon:
        return scaled_weapon_for_damage_multiplier(weapon, damage_multiplier)

    def _consumable_damage_power(self, attacker: Character, item: Consumable) -> float:
        spell_name = str(getattr(item, "spellName", "") or "").strip()
        if spell_name:
            referenced_spell = self.spell_service.get_spell(spell_name)
            if referenced_spell is not None:
                return self._adjusted_spell_power(attacker, referenced_spell)
        return max(0.0, float(getattr(item, "effectPower", 0.0) or 0.0))

    def _consumable_healing(self, attacker: Character, item: Consumable) -> float:
        spell_name = str(getattr(item, "spellName", "") or "").strip()
        if spell_name:
            referenced_spell = self.spell_service.get_spell(spell_name)
            if referenced_spell is not None:
                return self._adjusted_spell_power(attacker, referenced_spell)
        base = max(0.0, float(getattr(item, "effectPower", 0.0) or 0.0))
        if item.consumableKind == ConsumableKind.FOOD:
            return base * battle_factor("food_healing_multiplier", 0.8)
        return base

    @staticmethod
    def _health_state(character: Character) -> HealthState:
        return health_state_for_character(character)

    @staticmethod
    def _roll_hit_location(rng: random.Random) -> HitLocation:
        return roll_hit_location(rng)

    @staticmethod
    def _default_unarmed_weapon() -> Weapon:
        return Weapon(
            name="Unarmed Strike",
            damageMin=4.0,
            damageMax=6.0,
            armorMultiplier=0.7,
            ignoreArmorFraction=0.0,
            penetrationBase=2.0,
            staminaCost=default_offensive_action_stamina_cost(),
        )

