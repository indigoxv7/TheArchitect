from enum import Enum
from typing import Any


class SpellComponent(Enum):
    VERBAL = "verbal"
    SOMATIC = "somatic"
    MATERIAL = "material"


class AffinityTypes(Enum):
    CHI = "Chi"
    MANA = "Mana"
    PSI = "Psi"
    AETHER = "Aether"


class Spell:
    def __init__(
        self,
        name: str,
        level: int,
        power: float,
        affinity: AffinityTypes,
        powerLevel: float = 0.0,
        casting_time: float = 0,
        range: float = 0,
        components: dict[str, Any] = None,
        duration: float = 0,
        description: str = "",
        higher_level: str = None,
    ):
        self.name = name
        self.level = level
        self.power = power
        self.powerLevel = self._coerce_float(powerLevel, 0.0)
        self.affinity = affinity
        self.casting_time = casting_time
        self.range = range
        self.components = components if components is not None else {}
        self.duration = duration
        self.description = description
        self.higher_level = higher_level

    @staticmethod
    def _normalize_components(value: Any) -> dict[str, Any]:
        normalized = {"verbal": False, "somatic": False, "material": False}

        if isinstance(value, list):
            lowered = {str(item).strip().lower() for item in value}
            normalized["verbal"] = "verbal" in lowered
            normalized["somatic"] = "somatic" in lowered
            normalized["material"] = "material" if "material" in lowered else False
            return normalized

        if isinstance(value, dict):
            for key in ("verbal", "somatic", "material"):
                if key in value:
                    normalized[key] = value[key]
            return normalized

        return normalized

    @staticmethod
    def _normalize_affinity(value: Any) -> AffinityTypes:
        if isinstance(value, AffinityTypes):
            return value

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return AffinityTypes.MANA

            upper = text.upper()
            if upper in AffinityTypes.__members__:
                return AffinityTypes[upper]

            for affinity in AffinityTypes:
                if affinity.value.lower() == text.lower():
                    return affinity

        return AffinityTypes.MANA

    @staticmethod
    def _coerce_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except TypeError, ValueError:
            return default

    def to_dict(self) -> dict[str, Any]:
        affinity_value = self.affinity.value if isinstance(self.affinity, AffinityTypes) else str(self.affinity)
        return {
            "name": self.name,
            "level": int(self.level),
            "power": self.power,
            "powerLevel": self._coerce_float(self.powerLevel),
            "affinity": affinity_value,
            "casting_time": self._coerce_float(self.casting_time),
            "range": self._coerce_float(self.range),
            "components": self._normalize_components(self.components),
            "duration": self._coerce_float(self.duration),
            "description": self.description,
            "higher_level": self.higher_level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Spell":
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("Spell data must include a non-empty 'name'.")

        return cls(
            name=name,
            level=int(data.get("level", 0) or 0),
            power=data.get("power", ""),
            powerLevel=cls._coerce_float(data.get("powerLevel", 0.0), 0.0),
            affinity=cls._normalize_affinity(data.get("affinity", AffinityTypes.MANA.value)),
            casting_time=cls._coerce_float(data.get("casting_time", 0.0), 0.0),
            range=cls._coerce_float(data.get("range", 0.0), 0.0),
            components=cls._normalize_components(data.get("components", {})),
            duration=cls._coerce_float(data.get("duration", 0.0), 0.0),
            description=str(data.get("description", "")),
            higher_level=data.get("higher_level"),
        )

    def cast_spell(self, caster, target):
        if not self.has_required_components(caster):
            return f"{caster.name} does not have the required components to cast {self.name}."

        result = f"{caster.name} casts {self.name} on {target.name}."
        result += f"\n{self.description}"

        if self.higher_level:
            result += f"\nAt higher levels: {self.higher_level}"

        return result

    def has_required_components(self, caster):
        if self.components.get("verbal") and not caster.has_verbal_component():
            return False
        if self.components.get("somatic") and not caster.has_somatic_component():
            return False
        if self.components.get("material") and not caster.has_material_component(self.components["material"]):
            return False

        return True

    def __str__(self):
        components = ", ".join(
            [
                "V" if self.components.get("verbal") else "",
                "S" if self.components.get("somatic") else "",
                f"M ({self.components['material']})" if self.components.get("material") else "",
            ]
        ).strip(", ")

        affinity_value = self.affinity.value if isinstance(self.affinity, AffinityTypes) else str(self.affinity)
        spell_info = (
            f"Name: {self.name}\n"
            f"Level: {self.level}\n"
            f"Affinity: {affinity_value}\n"
            f"Casting Time: {self.casting_time}\n"
            f"Range: {self.range}\n"
            f"Components: {components}\n"
            f"Duration: {self.duration}\n"
            f"Description: {self.description}"
        )

        if self.higher_level:
            spell_info += f"\nAt Higher Levels: {self.higher_level}"

        return spell_info
