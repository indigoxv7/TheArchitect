from __future__ import annotations

from typing import Any

from src.domain.character_util import Achievement, Affinities, Attribute, AttributeBonus, Bonus, BonusType
from src.persistence.achievementbook_store import AchievementbookStore
from src.services.game_context import GameContext


class AchievementService:
    def __init__(self, achievementbook_path: str, context: GameContext):
        self.context = context
        self.store = AchievementbookStore(achievementbook_path)

    @staticmethod
    def _enum_from_name(enum_cls, value: Any, default):
        if isinstance(value, enum_cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().upper()
            if normalized in enum_cls.__members__:
                return enum_cls[normalized]
        return default

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _coerce_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @classmethod
    def _attribute_bonus_to_dict(cls, attribute_bonus: AttributeBonus | None) -> dict[str, Any] | None:
        if attribute_bonus is None:
            return None
        return {
            "attribute": attribute_bonus.attribute.name,
            "bonus": cls._coerce_int(attribute_bonus.bonus, 0),
        }

    @classmethod
    def _attribute_bonus_from_dict(cls, data: Any) -> AttributeBonus | None:
        if not isinstance(data, dict):
            return None

        attribute = cls._enum_from_name(Attribute, data.get("attribute"), None)
        if attribute is None:
            return None

        return AttributeBonus(attribute=attribute, bonus=cls._coerce_int(data.get("bonus", 0), 0))

    @classmethod
    def _bonus_to_dict(cls, bonus: Bonus | None) -> dict[str, Any] | None:
        if bonus is None:
            return None

        return {
            "bonusType": bonus.bonusType.name,
            "attributeBonus": cls._attribute_bonus_to_dict(bonus.attributeBonus),
            "affinities": {
                "chi": cls._coerce_float(bonus.affinities.chi, 0.0),
                "mana": cls._coerce_float(bonus.affinities.mana, 0.0),
                "psi": cls._coerce_float(bonus.affinities.psi, 0.0),
                "aether": cls._coerce_float(bonus.affinities.aether, 0.0),
            }
            if bonus.affinities is not None
            else None,
            "nanoMultiplier": cls._coerce_float(bonus.nanoMultiplier, 0.0),
            "reason": str(bonus.reason or ""),
            "permanent": bool(bonus.permanent),
        }

    @classmethod
    def _bonus_from_dict(cls, data: Any) -> Bonus | None:
        if not isinstance(data, dict):
            return None

        bonus_type = cls._enum_from_name(BonusType, data.get("bonusType"), BonusType.FLAT)
        affinities_data = data.get("affinities")
        affinities = None
        if isinstance(affinities_data, dict):
            affinities = Affinities(
                chi=cls._coerce_float(affinities_data.get("chi", 0.0), 0.0),
                mana=cls._coerce_float(affinities_data.get("mana", 0.0), 0.0),
                psi=cls._coerce_float(affinities_data.get("psi", 0.0), 0.0),
                aether=cls._coerce_float(affinities_data.get("aether", 0.0), 0.0),
            )

        return Bonus(
            bonusType=bonus_type,
            attributeBonus=cls._attribute_bonus_from_dict(data.get("attributeBonus")),
            affinities=affinities,
            nanoMultiplier=cls._coerce_float(data.get("nanoMultiplier", 0.0), 0.0),
            reason=str(data.get("reason", "") or ""),
            permanent=bool(data.get("permanent", False)),
        )

    @classmethod
    def _achievement_to_dict(cls, achievement: Achievement) -> dict[str, Any]:
        bonuses = [cls._bonus_to_dict(entry) for entry in getattr(achievement, "bonuses", []) if entry is not None]
        first_bonus = bonuses[0] if bonuses else None
        return {
            "name": str(achievement.name or ""),
            "title": str(achievement.title or ""),
            "description": str(getattr(achievement, "description", "") or ""),
            "bonuses": bonuses,
            # Backward compatibility for old readers.
            "bonus": first_bonus,
        }

    @classmethod
    def _achievement_from_dict(cls, data: Any) -> Achievement | None:
        if not isinstance(data, dict):
            return None

        name = str(data.get("name", "") or "").strip()
        if not name:
            return None

        bonuses: list[Bonus] = []
        raw_bonuses = data.get("bonuses")
        if isinstance(raw_bonuses, list):
            for raw_bonus in raw_bonuses:
                parsed = cls._bonus_from_dict(raw_bonus)
                if parsed is not None:
                    bonuses.append(parsed)
        else:
            parsed = cls._bonus_from_dict(data.get("bonus"))
            if parsed is not None:
                bonuses.append(parsed)

        return Achievement(
            name=name,
            title=str(data.get("title", "") or ""),
            description=str(data.get("description", "") or ""),
            bonuses=bonuses,
        )

    def load_achievementbook(self):
        payload = self.store.load()
        raw_achievements = payload.get("achievements", [])

        self.context.global_achievementbook.clear()
        for item in raw_achievements:
            achievement = self._achievement_from_dict(item)
            if achievement is None:
                continue
            self.context.global_achievementbook[achievement.name] = achievement

        self.context.achievementbook_overview = self.build_achievementbook_overview()

    def save_achievementbook(self):
        achievements = [self._achievement_to_dict(achievement) for achievement in self.list_achievements()]
        payload = {"format_version": 1, "achievements": achievements}
        self.store.save(payload)
        self.context.achievementbook_overview = self.build_achievementbook_overview()

    def list_achievements(self) -> list[Achievement]:
        return [
            self.context.global_achievementbook[name] for name in sorted(self.context.global_achievementbook.keys())
        ]

    def get_achievement(self, name: str) -> Achievement | None:
        return self.context.global_achievementbook.get(str(name or "").strip())

    def create_achievement_from_dict(self, data: dict):
        achievement = self._achievement_from_dict(data)
        if achievement is None:
            raise ValueError("Achievement payload must include a non-empty name.")
        if achievement.name in self.context.global_achievementbook:
            raise ValueError(f"Achievement '{achievement.name}' already exists.")

        self.context.global_achievementbook[achievement.name] = achievement
        self.save_achievementbook()

    def edit_achievement_from_patch(self, achievement_name: str, patch: dict):
        existing = self.get_achievement(achievement_name)
        if existing is None:
            raise ValueError(f"Achievement '{achievement_name}' does not exist.")

        merged = self._achievement_to_dict(existing)
        merged.update(patch or {})
        if not str(merged.get("name", "")).strip():
            merged["name"] = existing.name

        updated = self._achievement_from_dict(merged)
        if updated is None:
            raise ValueError("Updated achievement payload is invalid.")

        if updated.name != existing.name:
            self.context.global_achievementbook.pop(existing.name, None)
        self.context.global_achievementbook[updated.name] = updated
        self.save_achievementbook()

    @classmethod
    def to_dict(cls, achievement: Achievement | None) -> dict[str, Any] | None:
        if achievement is None:
            return None
        return cls._achievement_to_dict(achievement)

    def build_achievementbook_overview(self, max_lines: int = 20) -> str:
        achievements = self.list_achievements()
        if not achievements:
            return "No achievements in achievementbook yet."

        lines = []
        for achievement in achievements[:max_lines]:
            description = str(getattr(achievement, "description", "") or "").strip()
            desc_preview = description if len(description) <= 40 else description[:37] + "..."
            lines.append(
                f"- {achievement.name} ({len(getattr(achievement, 'bonuses', []))} bonuses)"
                + (f" - {desc_preview}" if desc_preview else "")
            )

        if len(achievements) > max_lines:
            lines.append(f"... and {len(achievements) - max_lines} more")

        return "\n".join(lines)
