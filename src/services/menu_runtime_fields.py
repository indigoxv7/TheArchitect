from __future__ import annotations

import json

from src.domain.CharacterUtil import DEFAULT_DURABILITY, DamageType, EquipSlot, ItemType, PowerType


SPELL_FIELD_DEFAULTS = {
    "name": "",
    "level": "",
    "power": "",
    "affinity": "",
    "casting_time": "",
    "range": "",
    "component_verbal": False,
    "component_somatic": False,
    "component_material": False,
    "duration": "",
    "description": "",
    "higher_level": "",
}

ITEM_FIELD_DEFAULTS = {
    "name": "",
    "slot": EquipSlot.NOT_EQUIPABLE.name,
    "tier": 0,
    "durability": DEFAULT_DURABILITY,
    "item_type": ItemType.DEFAULT.name,
    "damage_type": "NONE",
    "power_type": "NONE",
    "power_value": 0,
    "power_spell_name": "",
    "stat_bonuses_json": "[]",
}

ATTRIBUTES_DRAFT_DEFAULTS = {
    "physical_power": 5,
    "physical_stamina": 5,
    "physical_resistance": 5,
    "magic_power": 5,
    "magic_stamina": 5,
    "magic_resistance": 5,
}

GEAR_DRAFT_DEFAULTS = {
    "head": "",
    "neck": "",
    "body": "",
    "hands": "",
    "ring": "",
    "legs": "",
    "feet": "",
    "primary_weapon": "",
    "offhand": "",
    "inventory_json": "[]",
}

BONUS_DRAFT_DEFAULTS = {
    "bonus_type": "FLAT",
    "attribute_bonus_json": "{}",
    "affinities_json": "{}",
    "nano_multiplier": 0.0,
    "reason": "",
    "permanent": False,
}

ACHIEVEMENT_DRAFT_DEFAULTS = {
    "name": "",
    "title": "",
    "bonus_json": "{}",
}


def _parse_non_empty_text(value: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("Value cannot be empty.")
    return text


def _parse_level(value: str) -> int:
    text = str(value).strip()
    level = int(text)
    if level < 0:
        raise ValueError("Level must be >= 0.")
    return level


def _parse_non_negative_int(value: str) -> int:
    text = str(value).strip()
    parsed = int(text)
    if parsed < 0:
        raise ValueError("Value must be >= 0.")
    return parsed


def _parse_bool_yes_no(value: str) -> bool:
    text = str(value).strip().lower()
    if text in {"y", "yes", "true", "1"}:
        return True
    if text in {"n", "no", "false", "0"}:
        return False
    raise ValueError("Use yes/no.")


def _parse_material(value: str):
    text = str(value).strip()
    if not text:
        return False
    if text.lower() in {"none", "false", "no"}:
        return False
    return text


def _parse_optional_text(value: str):
    text = str(value).strip()
    return text if text else ""


def _parse_float(value: str) -> float:
    return float(str(value).strip())


def _parse_json_object(value: str) -> str:
    text = str(value).strip() or "{}"
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Value must be a JSON object.")
    return json.dumps(parsed, ensure_ascii=False)


def _parse_json_list(value: str) -> str:
    text = str(value).strip() or "[]"
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("Value must be a JSON array.")
    return json.dumps(parsed, ensure_ascii=False)


def _parse_stat_bonuses_json(value: str) -> str:
    text = str(value).strip() or "[]"
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("Stat bonuses must be a JSON array.")
    return json.dumps(parsed, ensure_ascii=False)


SPELL_FIELD_EDIT_CONFIG = {
    "spellSetNameAction": ("name", "Spell Name", _parse_non_empty_text),
    "spellSetLevelAction": ("level", "Spell Level", _parse_level),
    "spellSetPowerAction": ("power", "Power", _parse_non_empty_text),
    "spellSetAffinityAction": ("affinity", "Affinity", _parse_non_empty_text),
    "spellSetCastingTimeAction": ("casting_time", "Casting Time", _parse_non_empty_text),
    "spellSetRangeAction": ("range", "Range", _parse_non_empty_text),
    "spellSetVerbalAction": ("component_verbal", "Verbal Component (yes/no)", _parse_bool_yes_no),
    "spellSetSomaticAction": ("component_somatic", "Somatic Component (yes/no)", _parse_bool_yes_no),
    "spellSetMaterialAction": ("component_material", "Material Component (text or none)", _parse_material),
    "spellSetDurationAction": ("duration", "Duration", _parse_non_empty_text),
    "spellSetDescriptionAction": ("description", "Description", _parse_non_empty_text),
    "spellSetHigherLevelAction": ("higher_level", "Higher Level Text (optional)", _parse_optional_text),
}

ITEM_FIELD_EDIT_CONFIG = {
    "itemSetNameAction": ("itemDraft", "name", "Item Name", _parse_non_empty_text),
    "itemSetTierAction": ("itemDraft", "tier", "Item Tier", _parse_non_negative_int),
    "itemSetDurabilityAction": ("itemDraft", "durability", "Durability", _parse_non_negative_int),
    "itemSetPowerValueAction": ("itemDraft", "power_value", "Power Value", _parse_non_negative_int),
    "itemSetSpellNameAction": ("itemDraft", "power_spell_name", "Power Spell Name (optional)", _parse_optional_text),
    "itemSetStatBonusesAction": ("itemDraft", "stat_bonuses_json", "Stat Bonuses JSON", _parse_stat_bonuses_json),
}

COMPONENT_FIELD_EDIT_CONFIG = {
    "attributesSetPhysicalPowerAction": ("attributesDraft", "physical_power", "Physical Power", _parse_non_negative_int),
    "attributesSetPhysicalStaminaAction": ("attributesDraft", "physical_stamina", "Physical Stamina", _parse_non_negative_int),
    "attributesSetPhysicalResistanceAction": ("attributesDraft", "physical_resistance", "Physical Resistance", _parse_non_negative_int),
    "attributesSetMagicPowerAction": ("attributesDraft", "magic_power", "Magic Power", _parse_non_negative_int),
    "attributesSetMagicStaminaAction": ("attributesDraft", "magic_stamina", "Magic Stamina", _parse_non_negative_int),
    "attributesSetMagicResistanceAction": ("attributesDraft", "magic_resistance", "Magic Resistance", _parse_non_negative_int),
    "gearSetHeadAction": ("gearDraft", "head", "Head Item Name", _parse_optional_text),
    "gearSetNeckAction": ("gearDraft", "neck", "Neck Item Name", _parse_optional_text),
    "gearSetBodyAction": ("gearDraft", "body", "Body Item Name", _parse_optional_text),
    "gearSetHandsAction": ("gearDraft", "hands", "Hands Item Name", _parse_optional_text),
    "gearSetRingAction": ("gearDraft", "ring", "Ring Item Name", _parse_optional_text),
    "gearSetLegsAction": ("gearDraft", "legs", "Legs Item Name", _parse_optional_text),
    "gearSetFeetAction": ("gearDraft", "feet", "Feet Item Name", _parse_optional_text),
    "gearSetPrimaryWeaponAction": ("gearDraft", "primary_weapon", "Primary Weapon Name", _parse_optional_text),
    "gearSetOffhandAction": ("gearDraft", "offhand", "Offhand Item Name", _parse_optional_text),
    "gearSetInventoryAction": ("gearDraft", "inventory_json", "Inventory JSON", _parse_json_list),
    "bonusSetBonusTypeAction": ("bonusDraft", "bonus_type", "Bonus Type", _parse_non_empty_text),
    "bonusSetAttributeBonusAction": ("bonusDraft", "attribute_bonus_json", "Attribute Bonus JSON", _parse_json_object),
    "bonusSetAffinitiesAction": ("bonusDraft", "affinities_json", "Affinities JSON", _parse_json_object),
    "bonusSetNanoMultiplierAction": ("bonusDraft", "nano_multiplier", "Nano Multiplier", _parse_float),
    "bonusSetReasonAction": ("bonusDraft", "reason", "Reason", _parse_optional_text),
    "bonusSetPermanentAction": ("bonusDraft", "permanent", "Permanent (yes/no)", _parse_bool_yes_no),
    "achievementSetNameAction": ("achievementDraft", "name", "Achievement Name", _parse_non_empty_text),
    "achievementSetTitleAction": ("achievementDraft", "title", "Achievement Title", _parse_optional_text),
    "achievementSetBonusAction": ("achievementDraft", "bonus_json", "Bonus JSON", _parse_json_object),
}

ITEM_ENUM_ACTIONS = {
    "itemSetSlot_NOT_EQUIPABLE_Action": ("slot", EquipSlot.NOT_EQUIPABLE.name),
    "itemSetSlot_HEAD_Action": ("slot", EquipSlot.HEAD.name),
    "itemSetSlot_NECK_Action": ("slot", EquipSlot.NECK.name),
    "itemSetSlot_BODY_Action": ("slot", EquipSlot.BODY.name),
    "itemSetSlot_HANDS_Action": ("slot", EquipSlot.HANDS.name),
    "itemSetSlot_RING_Action": ("slot", EquipSlot.RING.name),
    "itemSetSlot_LEGS_Action": ("slot", EquipSlot.LEGS.name),
    "itemSetSlot_FEET_Action": ("slot", EquipSlot.FEET.name),
    "itemSetSlot_PRIMARY_WEAPON_Action": ("slot", EquipSlot.PRIMARY_WEAPON.name),
    "itemSetSlot_OFFHAND_Action": ("slot", EquipSlot.OFFHAND.name),
    "itemSetType_DEFAULT_Action": ("item_type", ItemType.DEFAULT.name),
    "itemSetType_CONSUMABLE_Action": ("item_type", ItemType.CONSUMABLE.name),
    "itemSetType_MELEE_WEAPON_Action": ("item_type", ItemType.MELEE_WEAPON.name),
    "itemSetType_MELEE_THROWABLE_Action": ("item_type", ItemType.MELEE_THROWABLE.name),
    "itemSetType_RANGED_WEAPON_Action": ("item_type", ItemType.RANGED_WEAPON.name),
    "itemSetType_ARMOR_Action": ("item_type", ItemType.ARMOR.name),
    "itemSetDamage_NONE_Action": ("damage_type", "NONE"),
    "itemSetDamage_PIERCING_Action": ("damage_type", DamageType.PIERCING.name),
    "itemSetDamage_BLUDGEONING_Action": ("damage_type", DamageType.BLUDGEONING.name),
    "itemSetDamage_SLASHING_Action": ("damage_type", DamageType.SLASHING.name),
    "itemSetDamage_COLD_Action": ("damage_type", DamageType.COLD.name),
    "itemSetDamage_FIRE_Action": ("damage_type", DamageType.FIRE.name),
    "itemSetDamage_LIGHTNING_Action": ("damage_type", DamageType.LIGHTNING.name),
    "itemSetDamage_THUNDER_Action": ("damage_type", DamageType.THUNDER.name),
    "itemSetDamage_POISON_Action": ("damage_type", DamageType.POISON.name),
    "itemSetDamage_ACID_Action": ("damage_type", DamageType.ACID.name),
    "itemSetDamage_RADIANT_Action": ("damage_type", DamageType.RADIANT.name),
    "itemSetDamage_NECROTIC_Action": ("damage_type", DamageType.NECROTIC.name),
    "itemSetDamage_FORCE_Action": ("damage_type", DamageType.FORCE.name),
    "itemSetDamage_PSYCHIC_Action": ("damage_type", DamageType.PSYCHIC.name),
    "itemSetPowerType_NONE_Action": ("power_type", "NONE"),
    "itemSetPowerType_PHYSICAL_ATTACK_Action": ("power_type", PowerType.PHYSICAL_ATTACK.name),
    "itemSetPowerType_MAGIC_ATTACK_Action": ("power_type", PowerType.MAGIC_ATTACK.name),
    "itemSetPowerType_CONSUMABLE_POWER_Action": ("power_type", PowerType.CONSUMABLE_POWER.name),
}
