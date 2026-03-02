from enum import Enum
from typing import Any


class SpellComponent(Enum):
    VERBAL = "verbal"
    SOMATIC = "somatic"
    MATERIAL = "material"


class Spell:
    def __init__(
        self,
        name,
        level,
        power,
        affinity,
        casting_time,
        range,
        components,
        duration,
        description,
        higher_level=None,
    ):
        self.name = name
        self.level = level
        self.power = power
        self.affinity = affinity
        self.casting_time = casting_time
        self.range = range
        self.components = components  # dict keys: verbal, somatic, material
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level,
            "power": self.power,
            "affinity": self.affinity,
            "casting_time": self.casting_time,
            "range": self.range,
            "components": self._normalize_components(self.components),
            "duration": self.duration,
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
            level=int(data.get("level", 0)),
            power=data.get("power", ""),
            affinity=data.get("affinity", ""),
            casting_time=data.get("casting_time", ""),
            range=data.get("range", ""),
            components=cls._normalize_components(data.get("components", {})),
            duration=data.get("duration", ""),
            description=data.get("description", ""),
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

        spell_info = (
            f"Name: {self.name}\n"
            f"Level: {self.level}\n"
            f"affinity: {self.affinity}\n"
            f"Casting Time: {self.casting_time}\n"
            f"Range: {self.range}\n"
            f"Components: {components}\n"
            f"Duration: {self.duration}\n"
            f"Description: {self.description}"
        )

        if self.higher_level:
            spell_info += f"\nAt Higher Levels: {self.higher_level}"

        return spell_info
