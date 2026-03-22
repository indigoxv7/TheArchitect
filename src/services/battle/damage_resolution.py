from __future__ import annotations

import copy
from typing import Any

from src.config.tuning import character_stat_factor
from src.domain.character_io import character_from_state
from src.domain.Character import Character, HealthState
from src.domain.character_util import Attributes, EquipSlot, HitLocation, ItemType
from src.domain.items import Weapon
from src.domain.Spells import Spell
from src.domain.combat.enums import BattleTeam, CombatRole
from src.domain.combat.state import BattleState, CommanderOrders
from src.domain.combat_timing import (
    ExertionLevel,
    accuracy_bonus_for_exertion,
    can_take_offensive_action,
    damage_multiplier_for_exertion,
    default_offensive_action_stamina_cost,
    defense_stat_penalty_for_exertion,
    spend_stamina,
    stamina_damage_from_hit,
    sync_stamina,
)
from src.domain.combat.units import EnemyStackState
from src.services.combat_loadout_service import select_active_character_weapon
from src.services.nano_display_service import format_nano


class BattleDamageResolutionMixin:
    def _character_snapshot_for_entity(self, battle: BattleState, entity) -> Character:
        serialized_state = getattr(entity, "character_state", None)
        if isinstance(serialized_state, dict) and serialized_state:
            try:
                source = character_from_state(
                    serialized_state,
                    item_resolver=self.item_service.get_item_by_id,
                    error_item=self.context.error_item,
                )
            except Exception:
                source = None
        elif getattr(entity, "team", BattleTeam.ALLY) == BattleTeam.ALLY and getattr(entity, "character_instance_id", ""):
            source = self._player_source_character(battle.player_id, getattr(entity, "character_instance_id", ""))
        else:
            source = self._template_character(
                getattr(entity, "template_character_id", ""),
                getattr(entity, "race_id", "Human1"),
            )
        if source is None:
            source = Character(name=self._entity_name(entity), attributes=Attributes())
        snapshot = copy.deepcopy(source)
        snapshot.health = int(max(0.0, self._entity_health(entity)))
        state_name = self._normalize_health_state_name(getattr(entity, "health_state", "HEALTHY"))
        snapshot.healthState = HealthState[state_name]
        if hasattr(snapshot, "CalculateBonus"):
            snapshot.CalculateBonus()
        return snapshot

    @staticmethod
    def _normalize_health_state_name(value: str) -> str:
        text = str(value or "HEALTHY").upper().strip()
        return text if text in HealthState.__members__ else "HEALTHY"

    def _default_unarmed_weapon(self) -> Weapon:
        return Weapon(
            name="Unarmed Strike",
            slot=EquipSlot.PRIMARY_WEAPON,
            tier=0,
            durability=100,
            itemType=ItemType.MELEE_WEAPON,
            damageType=[],
            damageMin=4.0,
            damageMax=6.0,
            armorMultiplier=0.7,
            ignoreArmorFraction=0.0,
            penetrationBase=2.0,
            staminaCost=default_offensive_action_stamina_cost(),
            itemId="UNARMED",
        )

    def _weapon_for_entity(self, entity) -> Weapon:
        primary = self.item_service.get_weapon_by_id(str(getattr(entity, "primary_weapon_item_id", "") or ""))
        if primary is not None:
            return primary
        offhand = self.item_service.get_weapon_by_id(str(getattr(entity, "offhand_item_id", "") or ""))
        if offhand is not None:
            return offhand
        return self._default_unarmed_weapon()

    def _spell_for_entity(self, entity) -> Spell | None:
        best_spell = None
        best_power = 0.0
        for name in getattr(entity, "spell_names", []) or []:
            spell = self.spell_service.get_spell(str(name))
            if spell is None:
                continue
            try:
                power = float(getattr(spell, "power", 0) or 0)
            except Exception:
                power = 0.0
            if power > best_power:
                best_power = power
                best_spell = spell
        return best_spell

    def _set_entity_health(self, entity, health: float):
        health = max(0.0, float(health))
        if isinstance(entity, EnemyStackState):
            entity.total_health = health
        else:
            entity.health = health
        entity.health_state = self._health_state_for_ratio(health, self._entity_max_health(entity)).name

    @staticmethod
    def _health_state_for_ratio(health: float, max_health: float) -> HealthState:
        if health <= 0:
            return HealthState.UNCONSCIOUS
        percent = (float(health) / max(1.0, float(max_health))) * 100.0
        if percent >= character_stat_factor("healthy_health_ratio_threshold", 0.76) * 100.0:
            return HealthState.HEALTHY
        if percent >= character_stat_factor("injured_health_ratio_threshold", 0.51) * 100.0:
            return HealthState.INJURED
        if percent >= character_stat_factor("heavily_injured_health_ratio_threshold", 0.26) * 100.0:
            return HealthState.HEAVILY_INJURED
        return HealthState.DYING

    def _apply_damage(self, entity, amount: float) -> float:
        before = self._entity_health(entity)
        after = max(0.0, before - max(0.0, float(amount)))
        self._set_entity_health(entity, after)
        return before - after

    def _apply_damage_with_result(self, entity, amount: float) -> dict[str, Any]:
        before_health = self._entity_health(entity)
        before_count = self._entity_count(entity)
        actual_damage = self._apply_damage(entity, amount)
        after_count = self._entity_count(entity)
        return {
            "damage": actual_damage,
            "defeated_units": max(0, before_count - after_count),
            "target_down": before_health > 0.0 and self._entity_health(entity) <= 0.0,
        }

    def _heal_entity(self, entity, amount: float) -> float:
        before = self._entity_health(entity)
        after = min(self._entity_max_health(entity), before + max(0.0, float(amount)))
        self._set_entity_health(entity, after)
        return after - before

    def _record_damage_taken(self, battle: BattleState, entity, amount: float):
        target = self._tracked_main_character(battle, entity)
        if target is None:
            return
        target.stats.record_damage_taken(amount)

    def _record_damage_done(self, battle: BattleState, entity, amount: float):
        attacker = self._tracked_main_character(battle, entity)
        if attacker is None:
            return
        attacker.stats.record_damage_done(amount)

    def _record_spell_cast(self, battle: BattleState, entity):
        attacker = self._tracked_main_character(battle, entity)
        if attacker is None:
            return
        attacker.stats.record_spell_cast()

    def _battle_team_highest_level(self, battle: BattleState) -> int:
        highest = 0
        for entity in getattr(battle, "ally_units", []) or []:
            if not bool(getattr(entity, "is_player_owned", False)):
                continue
            highest = max(highest, int(getattr(entity, "level", 0) or 0))
        return highest

    def _resolve_weapon_reference(self, item_like) -> Weapon | None:
        if isinstance(item_like, Weapon):
            return item_like
        item_id = str(getattr(item_like, "itemId", "") or item_like or "").strip()
        if not item_id:
            return None
        return self.item_service.get_weapon(item_id)

    def _character_has_penalized_equipment(self, character) -> bool:
        gear = getattr(character, "gear", None)
        if gear is None:
            return False
        items = []
        get_all_equipped = getattr(gear, "GetAllEquipped", None)
        if callable(get_all_equipped):
            items.extend(get_all_equipped())
        items.extend(getattr(gear, "inventory", []) or [])
        for item in items:
            weapon = self._resolve_weapon_reference(item)
            if weapon is not None and bool(getattr(weapon, "penalizedEquipment", False)):
                return True
        return False

    def _battle_has_penalized_equipment(self, battle: BattleState) -> bool:
        if not str(getattr(battle, "mission_id", "") or "").strip() and str(getattr(battle, "origin_type", "") or "") != "mission_node":
            return False
        for entity in getattr(battle, "ally_units", []) or []:
            if not bool(getattr(entity, "is_player_owned", False)):
                continue
            character = self._player_source_character(battle.player_id, getattr(entity, "character_instance_id", ""))
            if character is not None and self._character_has_penalized_equipment(character):
                return True
        player = self.player_service.get_player_sync(battle.player_id)
        if player is None:
            return False
        for entry in getattr(player, "inventory", []) or []:
            weapon = self._resolve_weapon_reference(entry)
            if weapon is not None and bool(getattr(weapon, "penalizedEquipment", False)):
                return True
        return False

    def _format_nano_reward_message(self, target_entity, nano_reward: int, count: int) -> str:
        unit_type = self._entity_name(target_entity)
        reward_text = format_nano(nano_reward)
        if int(count or 0) <= 1:
            return f"You have killed a {unit_type}. For your effort, you have received {reward_text} nano."
        return f"You have killed {int(count)} {unit_type}(s). For your effort, you have received {reward_text} nano."

    def _award_nano_for_enemy_kill(self, battle: BattleState, target_entity, count: int):
        if not bool(getattr(battle, "record_external_effects", True)):
            return None
        if self.nano_reward_calculator is None or int(count or 0) <= 0:
            return None
        if getattr(target_entity, "team", BattleTeam.ALLY) != BattleTeam.ENEMY:
            return None
        player = self.player_service.get_player_sync(battle.player_id)
        if player is None:
            return None
        target_character = self._character_snapshot_for_entity(battle, target_entity)
        reward = self.nano_reward_calculator.calculate_for_character(
            target_character,
            enemy_level=int(getattr(target_entity, "level", getattr(target_character, "level", 0)) or 0),
            team_highest_level=self._battle_team_highest_level(battle),
            penalized_equipment=self._battle_has_penalized_equipment(battle),
            defeated_count=int(count or 0),
        )
        if reward.totalNano <= 0:
            return reward
        player.nano = int(getattr(player, "nano", 0) or 0) + int(reward.totalNano)
        self.player_service.persist_player(player)
        return reward

    def _record_kill(self, battle: BattleState, attacker_entity, target_entity, count: int):
        attacker = self._tracked_main_character(battle, attacker_entity)
        if attacker is not None:
            is_boss = bool(getattr(target_entity, "is_boss", False))
            is_elite = bool(getattr(target_entity, "is_elite", False))
            attacker.stats.record_kill(self._entity_name(target_entity), count=count, is_boss=is_boss, is_elite=is_elite)
        if bool(getattr(target_entity, "is_boss", False)):
            battle.mission_statistics.bossesDefeated += count
        return self._award_nano_for_enemy_kill(battle, target_entity, count)

    def _resolve_attack(
        self,
        battle: BattleState,
        attacker,
        target,
        orders: CommanderOrders | None,
        highlights: list[str],
        current_time: float | None = None,
    ) -> bool:
        if target is None or self._entity_health(target) <= 0.0 or self._entity_health(attacker) <= 0.0:
            return False
        current_time = battle.battle_time_seconds if current_time is None else float(current_time)
        self._ensure_entity_runtime(attacker, current_time)
        self._ensure_entity_runtime(target, current_time)
        sync_stamina(attacker, current_time)
        sync_stamina(target, current_time)
        if not can_take_offensive_action(getattr(attacker, "exertion_level", ExertionLevel.FRESH.name)):
            return False
        attacker_character = self._character_snapshot_for_entity(battle, attacker)
        defender_character = self._character_snapshot_for_entity(battle, target)
        attack_bonus = self._stance_attack_bonus(orders) + accuracy_bonus_for_exertion(
            getattr(attacker, "exertion_level", ExertionLevel.FRESH.name)
        )
        if orders is not None:
            attack_bonus += float(orders.lane_discipline_modifier)
        congestion_penalty, firing_penalty, range_penalty = self._ranged_penalties(battle, attacker, target)

        weapon = (
            select_active_character_weapon(attacker_character, race_lookup=self._race_lookup)
            or self._default_unarmed_weapon()
        )
        spell = self._spell_for_entity(attacker)
        use_spell = False
        if spell is not None:
            try:
                use_spell = getattr(attacker, "role", CombatRole.FRONTLINE) != CombatRole.FRONTLINE or float(
                    getattr(spell, "power", 0) or 0
                ) >= float(getattr(weapon, "damageMax", 0) or 0)
            except Exception:
                use_spell = False

        if use_spell:
            self._record_spell_cast(battle, attacker)
            defender_magic_resistance = max(
                0.0,
                float(getattr(target, "magic_resistance", 5.0))
                - defense_stat_penalty_for_exertion(getattr(target, "exertion_level", ExertionLevel.FRESH.name)),
            )
            hit, hit_chance = self.damage_calculator.roll_hit(
                attacker_stat=float(getattr(attacker, "magic_power", 5.0)),
                defender_stat=defender_magic_resistance,
                congestion_penalty=congestion_penalty,
                firing_through_engagement_penalty=firing_penalty,
                range_penalty=range_penalty,
                bonus=attack_bonus,
            )
            breakdown = self.damage_calculator.calculate_magic_hit(
                attacker=attacker_character,
                defender=defender_character,
                spell_power=float(getattr(spell, "power", 0) or 0)
                * damage_multiplier_for_exertion(getattr(attacker, "exertion_level", ExertionLevel.FRESH.name)),
                hit_chance=hit_chance,
                did_hit=hit,
            )
            damage = breakdown.hpFinal if hit else 0.0
            if damage > 0:
                damage_result = self._apply_damage_with_result(target, damage)
                spend_stamina(target, stamina_damage_from_hit(damage_result["damage"]), current_time)
                self._record_damage_done(battle, attacker, damage_result["damage"])
                self._record_damage_taken(battle, target, damage_result["damage"])
                reward = None
                if damage_result["defeated_units"] > 0:
                    reward = self._record_kill(battle, attacker, target, damage_result["defeated_units"])
                highlights.append(
                    f"{self._entity_name(attacker)} blasts {self._entity_name(target)} for {damage_result['damage']:.1f} damage."
                )
                if reward is not None and int(getattr(reward, "totalNano", 0) or 0) > 0:
                    highlights.append(
                        self._format_nano_reward_message(target, reward.totalNano, damage_result["defeated_units"])
                    )
            else:
                highlights.append(
                    f"{self._entity_name(attacker)} misses {self._entity_name(target)} with {getattr(spell, 'name', 'a spell')}."
                )
            return True

        hit, _hit_chance = self.damage_calculator.roll_hit(
            attacker_stat=float(getattr(attacker, "physical_power", 5.0)),
            defender_stat=max(
                0.0,
                float(getattr(target, "physical_resistance", 5.0))
                - defense_stat_penalty_for_exertion(getattr(target, "exertion_level", ExertionLevel.FRESH.name)),
            ),
            congestion_penalty=congestion_penalty,
            firing_through_engagement_penalty=firing_penalty,
            range_penalty=range_penalty,
            bonus=attack_bonus,
        )
        if not hit:
            highlights.append(f"{self._entity_name(attacker)} misses {self._entity_name(target)}.")
            return True
        scaled_weapon = self._scaled_weapon_for_damage_multiplier(
            weapon,
            damage_multiplier_for_exertion(getattr(attacker, "exertion_level", ExertionLevel.FRESH.name)),
        )
        result = self.damage_calculator.calculate_physical_hit_to_location(
            attacker=attacker_character,
            defender=defender_character,
            weapon=scaled_weapon,
            location=HitLocation.BODY,
            applyArmorDamageToGear=False,
        )
        damage = max(0.0, result.hpFinal)
        if damage > 0:
            damage_result = self._apply_damage_with_result(target, damage)
            spend_stamina(target, stamina_damage_from_hit(damage_result["damage"]), current_time)
            self._record_damage_done(battle, attacker, damage_result["damage"])
            self._record_damage_taken(battle, target, damage_result["damage"])
            reward = None
            if damage_result["defeated_units"] > 0:
                reward = self._record_kill(battle, attacker, target, damage_result["defeated_units"])
            highlights.append(
                f"{self._entity_name(attacker)} hits {self._entity_name(target)} for {damage_result['damage']:.1f} damage."
            )
            if reward is not None and int(getattr(reward, "totalNano", 0) or 0) > 0:
                highlights.append(
                    self._format_nano_reward_message(target, reward.totalNano, damage_result["defeated_units"])
                )
        else:
            highlights.append(f"{self._entity_name(attacker)} fails to injure {self._entity_name(target)}.")
        return True

    @staticmethod
    def _scaled_weapon_for_damage_multiplier(weapon: Weapon, damage_multiplier: float) -> Weapon:
        if abs(float(damage_multiplier) - 1.0) < 0.0001:
            return weapon
        scaled_weapon = copy.deepcopy(weapon)
        scaled_weapon.damageMin = max(0.0, float(getattr(weapon, "damageMin", 0.0) or 0.0) * float(damage_multiplier))
        scaled_weapon.damageMax = max(
            scaled_weapon.damageMin,
            float(getattr(weapon, "damageMax", scaled_weapon.damageMin) or scaled_weapon.damageMin)
            * float(damage_multiplier),
        )
        return scaled_weapon

    def _offensive_action_cost(self, battle: BattleState, attacker) -> float:
        attacker_character = self._character_snapshot_for_entity(battle, attacker)
        weapon = (
            select_active_character_weapon(attacker_character, race_lookup=self._race_lookup)
            or self._default_unarmed_weapon()
        )
        spell = self._spell_for_entity(attacker)
        if spell is not None:
            try:
                if getattr(attacker, "role", CombatRole.FRONTLINE) != CombatRole.FRONTLINE or float(
                    getattr(spell, "power", 0) or 0
                ) >= float(getattr(weapon, "damageMax", 0) or 0):
                    return default_offensive_action_stamina_cost()
            except Exception:
                pass
        return max(
            0.0,
            float(
                getattr(weapon, "staminaCost", default_offensive_action_stamina_cost())
                or default_offensive_action_stamina_cost()
            ),
        )
