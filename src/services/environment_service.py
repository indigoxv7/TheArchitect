import re

from src.domain.environment import (
    Biome,
    Climate,
    CompatibilitySelectionMode,
    EnvironmentEffect,
    IncompatibilityMode,
    Terrain,
)
from src.persistence.environmentbook_store import EnvironmentbookStore
from src.services.game_context import GameContext


class EnvironmentService:
    def __init__(self, environmentbook_path: str, context: GameContext):
        self.context = context
        self.store = EnvironmentbookStore(environmentbook_path)

    @staticmethod
    def _slugify_name(name: str, fallback: str) -> str:
        compact = re.sub(r"\s+", "", str(name or "").strip())
        compact = re.sub(r"[^A-Za-z0-9_\-]", "", compact)
        return compact or fallback

    def _generate_id(self, collection: dict[str, object], name: str, fallback: str) -> str:
        prefix = self._slugify_name(name, fallback)
        index = len(collection)
        candidate = f"{prefix}{index}"
        while candidate in collection:
            index += 1
            candidate = f"{prefix}{index}"
        return candidate

    @staticmethod
    def _parse_label_id(label: str) -> str:
        text = str(label or "").strip()
        if text.endswith("]") and "[" in text:
            return text[text.rfind("[") + 1 : -1].strip()
        return text

    def get_effect_label(self, effect: EnvironmentEffect) -> str:
        return f"{effect.name} [{effect.effectId}]"

    def get_terrain_label(self, terrain: Terrain) -> str:
        return f"{terrain.name} [{terrain.terrainId}]"

    def get_climate_label(self, climate: Climate) -> str:
        summary = f"{climate.temperature or 'Any Temp'} / {climate.humidity or 'Any Humidity'}"
        return f"{climate.name} [{climate.climateId}] ({summary})"

    def get_biome_label(self, biome: Biome) -> str:
        return f"{biome.name} [{biome.biomeId}]"

    def load_environmentbook(self):
        payload = self.store.load()
        migrated = False
        self.context.all_environment_effects.clear()
        self.context.all_terrains.clear()
        self.context.all_climates.clear()
        self.context.all_biomes.clear()

        for raw in payload.get("effects", []) or []:
            try:
                effect = EnvironmentEffect.from_dict(raw)
            except Exception:
                continue
            if not effect.effectId or effect.effectId in self.context.all_environment_effects:
                effect.effectId = self._generate_id(self.context.all_environment_effects, effect.name, "Effect")
                migrated = True
            self.context.all_environment_effects[effect.effectId] = effect

        for raw in payload.get("terrains", []) or []:
            try:
                terrain = Terrain.from_dict(raw)
                self._validate_effect_refs(terrain.effectIds)
            except Exception:
                continue
            if not terrain.terrainId or terrain.terrainId in self.context.all_terrains:
                terrain.terrainId = self._generate_id(self.context.all_terrains, terrain.name, "Terrain")
                migrated = True
            self.context.all_terrains[terrain.terrainId] = terrain

        for raw in payload.get("climates", []) or []:
            try:
                climate = Climate.from_dict(raw)
                self._validate_effect_refs(climate.effectIds)
            except Exception:
                continue
            if not climate.climateId or climate.climateId in self.context.all_climates:
                climate.climateId = self._generate_id(self.context.all_climates, climate.name, "Climate")
                migrated = True
            self.context.all_climates[climate.climateId] = climate

        for raw in payload.get("biomes", []) or []:
            try:
                biome = Biome.from_dict(raw)
                self._validate_biome(biome)
            except Exception:
                continue
            if not biome.biomeId or biome.biomeId in self.context.all_biomes:
                biome.biomeId = self._generate_id(self.context.all_biomes, biome.name, "Biome")
                migrated = True
            self.context.all_biomes[biome.biomeId] = biome

        if migrated:
            self.save_environmentbook()
        else:
            self._refresh_overviews()

    def save_environmentbook(self):
        payload = {
            "format_version": 1,
            "effects": [effect.to_dict() for effect in self.list_effects()],
            "terrains": [terrain.to_dict() for terrain in self.list_terrains()],
            "climates": [climate.to_dict() for climate in self.list_climates()],
            "biomes": [biome.to_dict() for biome in self.list_biomes()],
        }
        self.store.save(payload)
        self._refresh_overviews()

    def _refresh_overviews(self):
        self.context.effectbook_overview = self.build_effect_overview()
        self.context.terrainbook_overview = self.build_terrain_overview()
        self.context.climatebook_overview = self.build_climate_overview()
        self.context.biomebook_overview = self.build_biome_overview()

    def _validate_effect_refs(self, effect_ids: list[str]):
        for effect_id in effect_ids:
            if self.get_effect_by_id(effect_id) is None:
                raise ValueError(f"Effect '{effect_id}' does not exist.")

    def _validate_biome(self, biome: Biome):
        self._validate_effect_refs(biome.effectIds)
        for terrain_id in biome.compatibleTerrainIds + biome.incompatibleTerrainIds:
            if self.get_terrain_by_id(terrain_id) is None:
                raise ValueError(f"Terrain '{terrain_id}' does not exist.")
        for climate_id in biome.compatibleClimateIds + biome.incompatibleClimateIds:
            if self.get_climate_by_id(climate_id) is None:
                raise ValueError(f"Climate '{climate_id}' does not exist.")

    def list_effects(self) -> list[EnvironmentEffect]:
        return sorted(self.context.all_environment_effects.values(), key=lambda effect: (effect.name.lower(), effect.effectId))

    def list_terrains(self) -> list[Terrain]:
        return sorted(self.context.all_terrains.values(), key=lambda terrain: (terrain.name.lower(), terrain.terrainId))

    def list_climates(self) -> list[Climate]:
        return sorted(self.context.all_climates.values(), key=lambda climate: (climate.name.lower(), climate.climateId))

    def list_biomes(self) -> list[Biome]:
        return sorted(self.context.all_biomes.values(), key=lambda biome: (biome.name.lower(), biome.biomeId))

    def get_effect_by_id(self, effect_id: str) -> EnvironmentEffect | None:
        return self.context.all_environment_effects.get(str(effect_id or "").strip())

    def get_terrain_by_id(self, terrain_id: str) -> Terrain | None:
        return self.context.all_terrains.get(str(terrain_id or "").strip())

    def get_climate_by_id(self, climate_id: str) -> Climate | None:
        return self.context.all_climates.get(str(climate_id or "").strip())

    def get_biome_by_id(self, biome_id: str) -> Biome | None:
        return self.context.all_biomes.get(str(biome_id or "").strip())

    def get_effect(self, identifier: str) -> EnvironmentEffect | None:
        key = str(identifier or "").strip()
        if not key:
            return None
        direct = self.get_effect_by_id(key)
        if direct is not None:
            return direct
        matches = [effect for effect in self.list_effects() if effect.name.lower() == key.lower()]
        return matches[0] if len(matches) == 1 else None

    def get_terrain(self, identifier: str) -> Terrain | None:
        key = str(identifier or "").strip()
        if not key:
            return None
        direct = self.get_terrain_by_id(key)
        if direct is not None:
            return direct
        matches = [terrain for terrain in self.list_terrains() if terrain.name.lower() == key.lower()]
        return matches[0] if len(matches) == 1 else None

    def get_climate(self, identifier: str) -> Climate | None:
        key = str(identifier or "").strip()
        if not key:
            return None
        direct = self.get_climate_by_id(key)
        if direct is not None:
            return direct
        matches = [climate for climate in self.list_climates() if climate.name.lower() == key.lower()]
        return matches[0] if len(matches) == 1 else None

    def get_biome(self, identifier: str) -> Biome | None:
        key = str(identifier or "").strip()
        if not key:
            return None
        direct = self.get_biome_by_id(key)
        if direct is not None:
            return direct
        matches = [biome for biome in self.list_biomes() if biome.name.lower() == key.lower()]
        return matches[0] if len(matches) == 1 else None

    def create_effect_from_dict(self, data: dict):
        effect = EnvironmentEffect.from_dict(data)
        if not effect.effectId:
            effect.effectId = self._generate_id(self.context.all_environment_effects, effect.name, "Effect")
        if effect.effectId in self.context.all_environment_effects:
            raise ValueError(f"Effect ID '{effect.effectId}' already exists.")
        self.context.all_environment_effects[effect.effectId] = effect
        self.save_environmentbook()
        return effect

    def edit_effect_from_patch(self, effect_identifier: str, patch: dict):
        existing = self.get_effect(effect_identifier)
        if existing is None:
            raise ValueError(f"Effect '{effect_identifier}' does not exist or is ambiguous.")
        merged = existing.to_dict()
        merged.update(patch or {})
        merged["effectId"] = existing.effectId
        if not str(merged.get("name", "") or "").strip():
            merged["name"] = existing.name
        updated = EnvironmentEffect.from_dict(merged)
        updated.effectId = existing.effectId
        self.context.all_environment_effects[updated.effectId] = updated
        self.save_environmentbook()
        return updated

    def create_terrain_from_dict(self, data: dict):
        terrain = Terrain.from_dict(data)
        self._validate_effect_refs(terrain.effectIds)
        if not terrain.terrainId:
            terrain.terrainId = self._generate_id(self.context.all_terrains, terrain.name, "Terrain")
        if terrain.terrainId in self.context.all_terrains:
            raise ValueError(f"Terrain ID '{terrain.terrainId}' already exists.")
        self.context.all_terrains[terrain.terrainId] = terrain
        self.save_environmentbook()
        return terrain

    def edit_terrain_from_patch(self, terrain_identifier: str, patch: dict):
        existing = self.get_terrain(terrain_identifier)
        if existing is None:
            raise ValueError(f"Terrain '{terrain_identifier}' does not exist or is ambiguous.")
        merged = existing.to_dict()
        merged.update(patch or {})
        merged["terrainId"] = existing.terrainId
        if not str(merged.get("name", "") or "").strip():
            merged["name"] = existing.name
        updated = Terrain.from_dict(merged)
        self._validate_effect_refs(updated.effectIds)
        updated.terrainId = existing.terrainId
        self.context.all_terrains[updated.terrainId] = updated
        self.save_environmentbook()
        return updated

    def create_climate_from_dict(self, data: dict):
        climate = Climate.from_dict(data)
        self._validate_effect_refs(climate.effectIds)
        if not climate.climateId:
            climate.climateId = self._generate_id(self.context.all_climates, climate.name, "Climate")
        if climate.climateId in self.context.all_climates:
            raise ValueError(f"Climate ID '{climate.climateId}' already exists.")
        self.context.all_climates[climate.climateId] = climate
        self.save_environmentbook()
        return climate

    def edit_climate_from_patch(self, climate_identifier: str, patch: dict):
        existing = self.get_climate(climate_identifier)
        if existing is None:
            raise ValueError(f"Climate '{climate_identifier}' does not exist or is ambiguous.")
        merged = existing.to_dict()
        merged.update(patch or {})
        merged["climateId"] = existing.climateId
        if not str(merged.get("name", "") or "").strip():
            merged["name"] = existing.name
        updated = Climate.from_dict(merged)
        self._validate_effect_refs(updated.effectIds)
        updated.climateId = existing.climateId
        self.context.all_climates[updated.climateId] = updated
        self.save_environmentbook()
        return updated

    def create_biome_from_dict(self, data: dict):
        biome = Biome.from_dict(data)
        self._validate_biome(biome)
        if not biome.biomeId:
            biome.biomeId = self._generate_id(self.context.all_biomes, biome.name, "Biome")
        if biome.biomeId in self.context.all_biomes:
            raise ValueError(f"Biome ID '{biome.biomeId}' already exists.")
        self.context.all_biomes[biome.biomeId] = biome
        self.save_environmentbook()
        return biome

    def edit_biome_from_patch(self, biome_identifier: str, patch: dict):
        existing = self.get_biome(biome_identifier)
        if existing is None:
            raise ValueError(f"Biome '{biome_identifier}' does not exist or is ambiguous.")
        merged = existing.to_dict()
        merged.update(patch or {})
        merged["biomeId"] = existing.biomeId
        if not str(merged.get("name", "") or "").strip():
            merged["name"] = existing.name
        updated = Biome.from_dict(merged)
        self._validate_biome(updated)
        updated.biomeId = existing.biomeId
        self.context.all_biomes[updated.biomeId] = updated
        self.save_environmentbook()
        return updated

    def build_effect_overview(self, max_lines: int = 20) -> str:
        effects = self.list_effects()
        if not effects:
            return "No effects in effectbook yet."
        lines = [f"- {effect.name} [{effect.effectId}]" for effect in effects[:max_lines]]
        if len(effects) > max_lines:
            lines.append(f"... and {len(effects) - max_lines} more")
        return "\n".join(lines)

    def build_terrain_overview(self, max_lines: int = 20) -> str:
        terrains = self.list_terrains()
        if not terrains:
            return "No terrains in terrainbook yet."
        lines = [f"- {terrain.name} [{terrain.terrainId}] ({len(terrain.effectIds)} effects)" for terrain in terrains[:max_lines]]
        if len(terrains) > max_lines:
            lines.append(f"... and {len(terrains) - max_lines} more")
        return "\n".join(lines)

    def build_climate_overview(self, max_lines: int = 20) -> str:
        climates = self.list_climates()
        if not climates:
            return "No climates in climatebook yet."
        lines = [
            f"- {climate.name} [{climate.climateId}] ({climate.temperature or 'Any Temp'} / {climate.humidity or 'Any Humidity'})"
            for climate in climates[:max_lines]
        ]
        if len(climates) > max_lines:
            lines.append(f"... and {len(climates) - max_lines} more")
        return "\n".join(lines)

    def build_biome_overview(self, max_lines: int = 20) -> str:
        biomes = self.list_biomes()
        if not biomes:
            return "No biomes in biomebook yet."
        lines = [f"- {biome.name} [{biome.biomeId}] ({len(biome.effectIds)} effects)" for biome in biomes[:max_lines]]
        if len(biomes) > max_lines:
            lines.append(f"... and {len(biomes) - max_lines} more")
        return "\n".join(lines)
