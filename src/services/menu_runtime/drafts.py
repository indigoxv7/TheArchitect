from __future__ import annotations

import json

from src.domain.character_util import DEFAULT_DURABILITY, EquipSlot, ItemType
from src.services.menu_runtime.fields import (
    ACHIEVEMENT_DRAFT_DEFAULTS,
    ATTRIBUTES_DRAFT_DEFAULTS,
    BONUS_DRAFT_DEFAULTS,
    GEAR_DRAFT_DEFAULTS,
    ITEM_FIELD_DEFAULTS,
    SPELL_FIELD_DEFAULTS,
)
from src.services.menu_runtime.parsers import build_item_payload_from_draft, build_spell_payload_from_draft
from src.ui.menu import MenuContext


class MenuRuntimeDraftMixin:
    @staticmethod
    def _build_spell_payload_from_draft(draft: dict) -> dict:
        return build_spell_payload_from_draft(draft)

    @staticmethod
    def _build_item_payload_from_draft(draft: dict) -> dict:
        return build_item_payload_from_draft(draft)

    @staticmethod
    def _start_spell_draft(menu_context: MenuContext, source_spell_name: str | None = None):
        menu_context.spellDraft = dict(SPELL_FIELD_DEFAULTS)
        menu_context.spellDraftActive = True
        menu_context.spellDraftSourceName = source_spell_name

    @staticmethod
    def _populate_spell_draft_from_spell(menu_context: MenuContext, spell):
        spell_data = spell.to_dict()
        components = spell_data.get("components", {})
        menu_context.spellDraft.update(
            {
                "name": spell_data.get("name", ""),
                "level": spell_data.get("level", 0),
                "power": spell_data.get("power", ""),
                "affinity": spell_data.get("affinity", ""),
                "casting_time": spell_data.get("casting_time", ""),
                "range": spell_data.get("range", ""),
                "component_verbal": bool(components.get("verbal", False)),
                "component_somatic": bool(components.get("somatic", False)),
                "component_material": components.get("material", False),
                "duration": spell_data.get("duration", ""),
                "description": spell_data.get("description", ""),
                "higher_level": spell_data.get("higher_level", ""),
            }
        )

    @staticmethod
    def _clear_spell_draft(menu_context: MenuContext):
        menu_context.spellDraft = {}
        menu_context.spellDraftActive = False
        menu_context.spellDraftSourceName = None

    @staticmethod
    def _start_item_draft(menu_context: MenuContext, source_item_id: str | None = None):
        menu_context.itemDraft = dict(ITEM_FIELD_DEFAULTS)
        menu_context.itemDraftActive = True
        menu_context.itemDraftSourceId = source_item_id
        menu_context.itemDraftSourceName = source_item_id

    @staticmethod
    def _populate_item_draft_from_item(menu_context: MenuContext, item):
        item_data = item.to_dict()
        damage_types = item_data.get("damageType", [])
        item_power = item_data.get("itemPower", [])
        first_power = item_power[0] if item_power else {}

        menu_context.itemDraft.update(
            {
                "name": item_data.get("name", ""),
                "slot": item_data.get("slot", EquipSlot.NOT_EQUIPABLE.name),
                "tier": int(item_data.get("tier", 0) or 0),
                "durability": int(item_data.get("durability", DEFAULT_DURABILITY) or DEFAULT_DURABILITY),
                "item_type": item_data.get("itemType", ItemType.DEFAULT.name),
                "damage_type": damage_types[0] if damage_types else "NONE",
                "power_type": str(first_power.get("powerType", "NONE") or "NONE"),
                "power_value": int(first_power.get("power", 0) or 0),
                "power_spell_name": str(first_power.get("spellName", "") or ""),
                "stat_bonuses_json": json.dumps(item_data.get("statBonuses", []), ensure_ascii=False),
            }
        )

    @staticmethod
    def _clear_item_draft(menu_context: MenuContext):
        menu_context.itemDraft = {}
        menu_context.itemDraftActive = False
        menu_context.itemDraftSourceId = None
        menu_context.itemDraftSourceName = None

    @staticmethod
    def _start_attributes_draft(menu_context: MenuContext):
        menu_context.attributesDraft = dict(ATTRIBUTES_DRAFT_DEFAULTS)
        menu_context.attributesDraftActive = True

    @staticmethod
    def _clear_attributes_draft(menu_context: MenuContext):
        menu_context.attributesDraft = {}
        menu_context.attributesDraftActive = False

    @staticmethod
    def _start_gear_draft(menu_context: MenuContext):
        menu_context.gearDraft = dict(GEAR_DRAFT_DEFAULTS)
        menu_context.gearDraftActive = True

    @staticmethod
    def _clear_gear_draft(menu_context: MenuContext):
        menu_context.gearDraft = {}
        menu_context.gearDraftActive = False

    @staticmethod
    def _start_bonus_draft(menu_context: MenuContext):
        menu_context.bonusDraft = dict(BONUS_DRAFT_DEFAULTS)
        menu_context.bonusDraftActive = True

    @staticmethod
    def _clear_bonus_draft(menu_context: MenuContext):
        menu_context.bonusDraft = {}
        menu_context.bonusDraftActive = False

    @staticmethod
    def _start_achievement_draft(menu_context: MenuContext):
        menu_context.achievementDraft = dict(ACHIEVEMENT_DRAFT_DEFAULTS)
        menu_context.achievementDraftActive = True

    @staticmethod
    def _clear_achievement_draft(menu_context: MenuContext):
        menu_context.achievementDraft = {}
        menu_context.achievementDraftActive = False

    def _refresh_spellbook_overview(self):
        self.context.spellbook_overview = self.spell_service.build_spellbook_overview()

    def _refresh_itembook_overview(self):
        self.context.itembook_overview = self.item_service.build_itembook_overview()
