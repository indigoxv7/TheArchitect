from __future__ import annotations

from src.config.tuning import battle_factor
from src.domain.character_util import PowerType
from src.domain.combat.enums import BattlePhase
from src.domain.items import Consumable, Item
from src.domain.combat.state import BattleState


class BattleConsumablesMixin:
    def _resolve_inventory_item(self, player, identifier) -> Item | None:
        if hasattr(identifier, "itemId"):
            return self.item_service.get_item_by_id(str(getattr(identifier, "itemId", "") or "")) or identifier
        if hasattr(identifier, "name"):
            return self.item_service.get_item(str(getattr(identifier, "itemId", "") or getattr(identifier, "name", "")))
        return self.item_service.get_item(str(identifier or ""))

    def list_available_consumables(self, battle: BattleState) -> list[tuple[str, str]]:
        player = self.player_service.get_player_sync(battle.player_id)
        if player is None:
            return []
        results = []
        for entry in getattr(player, "inventory", []) or []:
            item = self._resolve_inventory_item(player, entry)
            if not isinstance(item, Consumable):
                continue
            item_id = str(getattr(item, "itemId", "") or "")
            label = (
                self.item_service.get_item_label(item)
                if item_id
                else str(getattr(item, "name", "Consumable") or "Consumable")
            )
            results.append((item_id or label, label))
        return results

    def use_consumable(self, battle: BattleState, item_identifier: str) -> str:
        player = self.player_service.get_player_sync(battle.player_id)
        if player is None:
            raise ValueError("Player not found.")
        inventory = list(getattr(player, "inventory", []) or [])
        item = self.item_service.get_consumable(str(item_identifier or ""))
        if item is None:
            item = self.item_service.get_consumable_by_id(self.item_service.parse_item_id_from_label(item_identifier))
        if item is None:
            raise ValueError("Consumable not found.")

        removed = False
        remaining = []
        for entry in inventory:
            resolved = self._resolve_inventory_item(player, entry)
            if (
                not removed
                and resolved is not None
                and str(getattr(resolved, "itemId", "") or "") == str(getattr(item, "itemId", "") or "")
            ):
                removed = True
                continue
            remaining.append(entry)
        if not removed:
            raise ValueError("That consumable is not in the player's inventory.")
        player.inventory = remaining
        power_values = [
            power
            for power in getattr(item, "itemPower", []) or []
            if getattr(power, "powerType", None) == PowerType.CONSUMABLE_POWER
        ]
        amount = float(getattr(power_values[0], "power", 10) if power_values else 10)
        offensive = bool(getattr(item, "damageType", []))
        if offensive:
            allies = self._active_allies(battle)
            target_source = allies[0] if allies else None
            target = self._select_target(battle, target_source, self._active_enemies(battle), battle.orders)
            if target is None:
                raise ValueError("No valid enemy target for this consumable.")
            damage_result = self._apply_damage_with_result(target, amount)
            if damage_result["defeated_units"] > 0 and allies:
                self._record_kill(battle, allies[0], target, damage_result["defeated_units"])
            self._refresh_mission_state(battle, mission_complete=(battle.phase == BattlePhase.RESOLVED))
            message = f"Used {item.name} on {self._entity_name(target)} for {damage_result['damage']:.1f} damage."
        else:
            allies = self._active_allies(battle)
            if not allies:
                raise ValueError("No allied targets available.")
            target = min(
                allies, key=lambda entity: self._entity_health(entity) / max(1.0, self._entity_max_health(entity))
            )
            healed = self._heal_entity(
                target,
                amount
                * max(
                    battle_factor("minimum_resource_efficiency_multiplier", 0.5),
                    1.0 + battle.orders.resource_efficiency_modifier,
                ),
            )
            self._refresh_mission_state(battle, mission_complete=(battle.phase == BattlePhase.RESOLVED))
            message = f"Used {item.name} on {self._entity_name(target)} and restored {healed:.1f} health."
        self.player_service.persist_player(player)
        self.save_battle(battle)
        return message
