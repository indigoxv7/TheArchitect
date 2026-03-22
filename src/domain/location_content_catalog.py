from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.location_content_common import (
    CompatibilitySelectionMode,
    EnvironmentEffect,
    HookType,
    IncompatibilityMode,
    SceneDescriptionMode,
    WeightedTextFragment,
    clean_text,
    coerce_enum,
    normalize_payload_dict,
    normalize_string_map,
    normalize_tag_list,
    normalize_text_list,
)


@dataclass
class TerrainProfile:
    name: str
    description: str = ""
    canonicalTags: list[str] = field(default_factory=list)
    landformTags: list[str] = field(default_factory=list)
    traversalTags: list[str] = field(default_factory=list)
    visibilityTags: list[str] = field(default_factory=list)
    wetnessTags: list[str] = field(default_factory=list)
    obstacleTags: list[str] = field(default_factory=list)
    effectIds: list[str] = field(default_factory=list)
    terrainId: str = ""

    def __post_init__(self):
        self.name = clean_text(self.name)
        self.description = str(self.description or "")
        self.canonicalTags = normalize_tag_list(self.canonicalTags)
        self.landformTags = normalize_tag_list(self.landformTags)
        self.traversalTags = normalize_tag_list(self.traversalTags)
        self.visibilityTags = normalize_tag_list(self.visibilityTags)
        self.wetnessTags = normalize_tag_list(self.wetnessTags)
        self.obstacleTags = normalize_tag_list(self.obstacleTags)
        self.effectIds = normalize_text_list(self.effectIds)
        self.terrainId = clean_text(self.terrainId)

    @property
    def allTags(self) -> list[str]:
        return normalize_tag_list(
            self.canonicalTags
            + self.landformTags
            + self.traversalTags
            + self.visibilityTags
            + self.wetnessTags
            + self.obstacleTags
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "terrainId": self.terrainId,
            "name": self.name,
            "description": self.description,
            "canonicalTags": list(self.canonicalTags),
            "landformTags": list(self.landformTags),
            "traversalTags": list(self.traversalTags),
            "visibilityTags": list(self.visibilityTags),
            "wetnessTags": list(self.wetnessTags),
            "obstacleTags": list(self.obstacleTags),
            "effectIds": list(self.effectIds),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "TerrainProfile":
        if not isinstance(data, dict):
            raise ValueError("Terrain data must be a dictionary.")
        name = clean_text(data.get("name", ""))
        if not name:
            raise ValueError("Terrain data must include a non-empty name.")
        return cls(
            name=name,
            description=str(data.get("description", "") or ""),
            canonicalTags=data.get("canonicalTags", data.get("tags", [])),
            landformTags=data.get("landformTags", []),
            traversalTags=data.get("traversalTags", []),
            visibilityTags=data.get("visibilityTags", []),
            wetnessTags=data.get("wetnessTags", []),
            obstacleTags=data.get("obstacleTags", []),
            effectIds=data.get("effectIds", []),
            terrainId=clean_text(data.get("terrainId", "")),
        )


@dataclass
class ClimateProfile:
    name: str
    temperature: str = ""
    humidity: str = ""
    description: str = ""
    canonicalTags: list[str] = field(default_factory=list)
    weatherTags: list[str] = field(default_factory=list)
    floodTags: list[str] = field(default_factory=list)
    fogTags: list[str] = field(default_factory=list)
    seasonalityTags: list[str] = field(default_factory=list)
    effectIds: list[str] = field(default_factory=list)
    climateId: str = ""

    def __post_init__(self):
        self.name = clean_text(self.name)
        self.temperature = str(self.temperature or "")
        self.humidity = str(self.humidity or "")
        self.description = str(self.description or "")
        self.canonicalTags = normalize_tag_list(self.canonicalTags)
        self.weatherTags = normalize_tag_list(self.weatherTags)
        self.floodTags = normalize_tag_list(self.floodTags)
        self.fogTags = normalize_tag_list(self.fogTags)
        self.seasonalityTags = normalize_tag_list(self.seasonalityTags)
        self.effectIds = normalize_text_list(self.effectIds)
        self.climateId = clean_text(self.climateId)

    @property
    def allTags(self) -> list[str]:
        return normalize_tag_list(
            self.canonicalTags + self.weatherTags + self.floodTags + self.fogTags + self.seasonalityTags
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "climateId": self.climateId,
            "name": self.name,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "description": self.description,
            "canonicalTags": list(self.canonicalTags),
            "weatherTags": list(self.weatherTags),
            "floodTags": list(self.floodTags),
            "fogTags": list(self.fogTags),
            "seasonalityTags": list(self.seasonalityTags),
            "effectIds": list(self.effectIds),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "ClimateProfile":
        if not isinstance(data, dict):
            raise ValueError("Climate data must be a dictionary.")
        name = clean_text(data.get("name", ""))
        if not name:
            raise ValueError("Climate data must include a non-empty name.")
        return cls(
            name=name,
            temperature=str(data.get("temperature", data.get("temp", "")) or ""),
            humidity=str(data.get("humidity", "") or ""),
            description=str(data.get("description", "") or ""),
            canonicalTags=data.get("canonicalTags", data.get("tags", [])),
            weatherTags=data.get("weatherTags", []),
            floodTags=data.get("floodTags", []),
            fogTags=data.get("fogTags", []),
            seasonalityTags=data.get("seasonalityTags", []),
            effectIds=data.get("effectIds", []),
            climateId=clean_text(data.get("climateId", "")),
        )


@dataclass
class BiomeArchetype:
    name: str
    description: str = ""
    terrainCompatibilityMode: CompatibilitySelectionMode = CompatibilitySelectionMode.ANY
    compatibleTerrainIds: list[str] = field(default_factory=list)
    terrainIncompatibilityMode: IncompatibilityMode = IncompatibilityMode.EXPLICIT
    incompatibleTerrainIds: list[str] = field(default_factory=list)
    climateCompatibilityMode: CompatibilitySelectionMode = CompatibilitySelectionMode.ANY
    compatibleClimateIds: list[str] = field(default_factory=list)
    climateIncompatibilityMode: IncompatibilityMode = IncompatibilityMode.EXPLICIT
    incompatibleClimateIds: list[str] = field(default_factory=list)
    canonicalBaseTags: list[str] = field(default_factory=list)
    civilizationPriors: list[str] = field(default_factory=list)
    threatPriors: list[str] = field(default_factory=list)
    resourcePriors: list[str] = field(default_factory=list)
    mythicPriors: list[str] = field(default_factory=list)
    ecologyPriors: list[str] = field(default_factory=list)
    effectIds: list[str] = field(default_factory=list)
    biomeId: str = ""

    def __post_init__(self):
        self.name = clean_text(self.name)
        self.description = str(self.description or "")
        self.terrainCompatibilityMode = coerce_enum(
            CompatibilitySelectionMode,
            self.terrainCompatibilityMode,
            CompatibilitySelectionMode.ANY,
        )
        self.compatibleTerrainIds = normalize_text_list(self.compatibleTerrainIds)
        self.terrainIncompatibilityMode = coerce_enum(
            IncompatibilityMode,
            self.terrainIncompatibilityMode,
            IncompatibilityMode.EXPLICIT,
        )
        self.incompatibleTerrainIds = normalize_text_list(self.incompatibleTerrainIds)
        self.climateCompatibilityMode = coerce_enum(
            CompatibilitySelectionMode,
            self.climateCompatibilityMode,
            CompatibilitySelectionMode.ANY,
        )
        self.compatibleClimateIds = normalize_text_list(self.compatibleClimateIds)
        self.climateIncompatibilityMode = coerce_enum(
            IncompatibilityMode,
            self.climateIncompatibilityMode,
            IncompatibilityMode.EXPLICIT,
        )
        self.incompatibleClimateIds = normalize_text_list(self.incompatibleClimateIds)
        self.canonicalBaseTags = normalize_tag_list(self.canonicalBaseTags)
        self.civilizationPriors = normalize_tag_list(self.civilizationPriors)
        self.threatPriors = normalize_tag_list(self.threatPriors)
        self.resourcePriors = normalize_tag_list(self.resourcePriors)
        self.mythicPriors = normalize_tag_list(self.mythicPriors)
        self.ecologyPriors = normalize_tag_list(self.ecologyPriors)
        self.effectIds = normalize_text_list(self.effectIds)
        self.biomeId = clean_text(self.biomeId)

    @property
    def allTags(self) -> list[str]:
        return normalize_tag_list(
            self.canonicalBaseTags
            + self.civilizationPriors
            + self.threatPriors
            + self.resourcePriors
            + self.mythicPriors
            + self.ecologyPriors
        )

    def allows_terrain(self, terrain_id: str) -> bool:
        target = clean_text(terrain_id)
        if not target:
            return False
        if self.terrainCompatibilityMode == CompatibilitySelectionMode.SELECTED and target not in self.compatibleTerrainIds:
            return False
        if self.terrainIncompatibilityMode == IncompatibilityMode.EXPLICIT and target in self.incompatibleTerrainIds:
            return False
        if self.terrainIncompatibilityMode == IncompatibilityMode.ALL_EXCEPT_COMPATIBLE:
            return target in self.compatibleTerrainIds
        return True

    def allows_climate(self, climate_id: str) -> bool:
        target = clean_text(climate_id)
        if not target:
            return False
        if self.climateCompatibilityMode == CompatibilitySelectionMode.SELECTED and target not in self.compatibleClimateIds:
            return False
        if self.climateIncompatibilityMode == IncompatibilityMode.EXPLICIT and target in self.incompatibleClimateIds:
            return False
        if self.climateIncompatibilityMode == IncompatibilityMode.ALL_EXCEPT_COMPATIBLE:
            return target in self.compatibleClimateIds
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "biomeId": self.biomeId,
            "name": self.name,
            "description": self.description,
            "terrainCompatibilityMode": self.terrainCompatibilityMode.name,
            "compatibleTerrainIds": list(self.compatibleTerrainIds),
            "terrainIncompatibilityMode": self.terrainIncompatibilityMode.name,
            "incompatibleTerrainIds": list(self.incompatibleTerrainIds),
            "climateCompatibilityMode": self.climateCompatibilityMode.name,
            "compatibleClimateIds": list(self.compatibleClimateIds),
            "climateIncompatibilityMode": self.climateIncompatibilityMode.name,
            "incompatibleClimateIds": list(self.incompatibleClimateIds),
            "canonicalBaseTags": list(self.canonicalBaseTags),
            "civilizationPriors": list(self.civilizationPriors),
            "threatPriors": list(self.threatPriors),
            "resourcePriors": list(self.resourcePriors),
            "mythicPriors": list(self.mythicPriors),
            "ecologyPriors": list(self.ecologyPriors),
            "effectIds": list(self.effectIds),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "BiomeArchetype":
        if not isinstance(data, dict):
            raise ValueError("Biome data must be a dictionary.")
        name = clean_text(data.get("name", ""))
        if not name:
            raise ValueError("Biome data must include a non-empty name.")
        return cls(
            name=name,
            description=str(data.get("description", "") or ""),
            terrainCompatibilityMode=data.get("terrainCompatibilityMode", CompatibilitySelectionMode.ANY.name),
            compatibleTerrainIds=data.get("compatibleTerrainIds", []),
            terrainIncompatibilityMode=data.get("terrainIncompatibilityMode", IncompatibilityMode.EXPLICIT.name),
            incompatibleTerrainIds=data.get("incompatibleTerrainIds", []),
            climateCompatibilityMode=data.get("climateCompatibilityMode", CompatibilitySelectionMode.ANY.name),
            compatibleClimateIds=data.get("compatibleClimateIds", []),
            climateIncompatibilityMode=data.get("climateIncompatibilityMode", IncompatibilityMode.EXPLICIT.name),
            incompatibleClimateIds=data.get("incompatibleClimateIds", []),
            canonicalBaseTags=data.get("canonicalBaseTags", data.get("tags", [])),
            civilizationPriors=data.get("civilizationPriors", []),
            threatPriors=data.get("threatPriors", []),
            resourcePriors=data.get("resourcePriors", []),
            mythicPriors=data.get("mythicPriors", []),
            ecologyPriors=data.get("ecologyPriors", []),
            effectIds=data.get("effectIds", []),
            biomeId=clean_text(data.get("biomeId", "")),
        )

@dataclass
class NodeRoleTemplate:
    name: str
    description: str = ""
    weight: float = 1.0
    roleTags: list[str] = field(default_factory=list)
    requiredTags: list[str] = field(default_factory=list)
    excludedTags: list[str] = field(default_factory=list)
    desiredAffordanceTags: list[str] = field(default_factory=list)
    desiredHazardTags: list[str] = field(default_factory=list)
    desiredHookTypes: list[str] = field(default_factory=list)
    minFeatures: int = 1
    maxFeatures: int = 3
    roleId: str = ""

    def __post_init__(self):
        self.name = clean_text(self.name)
        self.description = str(self.description or "")
        self.weight = max(0.0, float(self.weight or 0.0))
        self.roleTags = normalize_tag_list(self.roleTags)
        self.requiredTags = normalize_tag_list(self.requiredTags)
        self.excludedTags = normalize_tag_list(self.excludedTags)
        self.desiredAffordanceTags = normalize_tag_list(self.desiredAffordanceTags)
        self.desiredHazardTags = normalize_tag_list(self.desiredHazardTags)
        self.desiredHookTypes = normalize_text_list(self.desiredHookTypes)
        self.minFeatures = max(0, int(self.minFeatures or 0))
        self.maxFeatures = max(self.minFeatures, int(self.maxFeatures or self.minFeatures))
        self.roleId = clean_text(self.roleId)

    def to_dict(self) -> dict[str, Any]:
        return {
            "roleId": self.roleId,
            "name": self.name,
            "description": self.description,
            "weight": float(self.weight),
            "roleTags": list(self.roleTags),
            "requiredTags": list(self.requiredTags),
            "excludedTags": list(self.excludedTags),
            "desiredAffordanceTags": list(self.desiredAffordanceTags),
            "desiredHazardTags": list(self.desiredHazardTags),
            "desiredHookTypes": list(self.desiredHookTypes),
            "minFeatures": int(self.minFeatures),
            "maxFeatures": int(self.maxFeatures),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "NodeRoleTemplate":
        if not isinstance(data, dict):
            raise ValueError("Node role data must be a dictionary.")
        name = clean_text(data.get("name", ""))
        if not name:
            raise ValueError("Node role data must include a non-empty name.")
        return cls(
            name=name,
            description=str(data.get("description", "") or ""),
            weight=float(data.get("weight", 1.0) or 1.0),
            roleTags=data.get("roleTags", []),
            requiredTags=data.get("requiredTags", []),
            excludedTags=data.get("excludedTags", []),
            desiredAffordanceTags=data.get("desiredAffordanceTags", []),
            desiredHazardTags=data.get("desiredHazardTags", []),
            desiredHookTypes=data.get("desiredHookTypes", []),
            minFeatures=int(data.get("minFeatures", 1) or 1),
            maxFeatures=int(data.get("maxFeatures", 3) or 3),
            roleId=clean_text(data.get("roleId", "")),
        )


@dataclass
class FeatureTemplate:
    name: str
    category: str = "ambient"
    description: str = ""
    weight: float = 1.0
    requiredTags: list[str] = field(default_factory=list)
    excludedTags: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    affordanceTags: list[str] = field(default_factory=list)
    hazardTags: list[str] = field(default_factory=list)
    memoryTags: list[str] = field(default_factory=list)
    visibleTags: list[str] = field(default_factory=list)
    hookTypeSuggestions: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    localDescriptionHints: list[str] = field(default_factory=list)
    featureId: str = ""

    def __post_init__(self):
        self.name = clean_text(self.name)
        self.category = clean_text(self.category) or "ambient"
        self.description = str(self.description or "")
        self.weight = max(0.0, float(self.weight or 0.0))
        self.requiredTags = normalize_tag_list(self.requiredTags)
        self.excludedTags = normalize_tag_list(self.excludedTags)
        self.tags = normalize_tag_list(self.tags)
        self.affordanceTags = normalize_tag_list(self.affordanceTags)
        self.hazardTags = normalize_tag_list(self.hazardTags)
        self.memoryTags = normalize_tag_list(self.memoryTags)
        self.visibleTags = normalize_tag_list(self.visibleTags)
        self.hookTypeSuggestions = normalize_text_list(self.hookTypeSuggestions)
        self.metrics = normalize_string_map(self.metrics)
        self.payload = normalize_payload_dict(self.payload)
        self.localDescriptionHints = normalize_text_list(self.localDescriptionHints)
        self.featureId = clean_text(self.featureId)

    def to_dict(self) -> dict[str, Any]:
        return {
            "featureId": self.featureId,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "weight": float(self.weight),
            "requiredTags": list(self.requiredTags),
            "excludedTags": list(self.excludedTags),
            "tags": list(self.tags),
            "affordanceTags": list(self.affordanceTags),
            "hazardTags": list(self.hazardTags),
            "memoryTags": list(self.memoryTags),
            "visibleTags": list(self.visibleTags),
            "hookTypeSuggestions": list(self.hookTypeSuggestions),
            "metrics": dict(self.metrics),
            "payload": dict(self.payload),
            "localDescriptionHints": list(self.localDescriptionHints),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "FeatureTemplate":
        if not isinstance(data, dict):
            raise ValueError("Feature template data must be a dictionary.")
        name = clean_text(data.get("name", ""))
        if not name:
            raise ValueError("Feature template data must include a non-empty name.")
        return cls(
            name=name,
            category=str(data.get("category", "ambient") or "ambient"),
            description=str(data.get("description", "") or ""),
            weight=float(data.get("weight", 1.0) or 1.0),
            requiredTags=data.get("requiredTags", []),
            excludedTags=data.get("excludedTags", []),
            tags=data.get("tags", []),
            affordanceTags=data.get("affordanceTags", []),
            hazardTags=data.get("hazardTags", []),
            memoryTags=data.get("memoryTags", []),
            visibleTags=data.get("visibleTags", []),
            hookTypeSuggestions=data.get("hookTypeSuggestions", []),
            metrics=data.get("metrics", {}),
            payload=data.get("payload", {}),
            localDescriptionHints=data.get("localDescriptionHints", []),
            featureId=clean_text(data.get("featureId", "")),
        )


@dataclass
class HookTemplate:
    name: str
    hookType: HookType = HookType.LORE
    description: str = ""
    weight: float = 1.0
    requiredTags: list[str] = field(default_factory=list)
    excludedTags: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    memoryTags: list[str] = field(default_factory=list)
    visibleText: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    hookId: str = ""

    def __post_init__(self):
        self.name = clean_text(self.name)
        self.hookType = coerce_enum(HookType, self.hookType, HookType.LORE)
        self.description = str(self.description or "")
        self.weight = max(0.0, float(self.weight or 0.0))
        self.requiredTags = normalize_tag_list(self.requiredTags)
        self.excludedTags = normalize_tag_list(self.excludedTags)
        self.tags = normalize_tag_list(self.tags)
        self.memoryTags = normalize_tag_list(self.memoryTags)
        self.visibleText = str(self.visibleText or "")
        self.payload = normalize_payload_dict(self.payload)
        self.hookId = clean_text(self.hookId)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hookId": self.hookId,
            "name": self.name,
            "hookType": self.hookType.name,
            "description": self.description,
            "weight": float(self.weight),
            "requiredTags": list(self.requiredTags),
            "excludedTags": list(self.excludedTags),
            "tags": list(self.tags),
            "memoryTags": list(self.memoryTags),
            "visibleText": self.visibleText,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "HookTemplate":
        if not isinstance(data, dict):
            raise ValueError("Hook template data must be a dictionary.")
        name = clean_text(data.get("name", ""))
        if not name:
            raise ValueError("Hook template data must include a non-empty name.")
        return cls(
            name=name,
            hookType=data.get("hookType", HookType.LORE.name),
            description=str(data.get("description", "") or ""),
            weight=float(data.get("weight", 1.0) or 1.0),
            requiredTags=data.get("requiredTags", []),
            excludedTags=data.get("excludedTags", []),
            tags=data.get("tags", []),
            memoryTags=data.get("memoryTags", []),
            visibleText=str(data.get("visibleText", "") or ""),
            payload=data.get("payload", {}),
            hookId=clean_text(data.get("hookId", "")),
        )


@dataclass
class DescriptionPack:
    name: str
    description: str = ""
    openaiHint: str = ""
    openingFragments: list[WeightedTextFragment] = field(default_factory=list)
    landmarkFragments: list[WeightedTextFragment] = field(default_factory=list)
    atmosphereFragments: list[WeightedTextFragment] = field(default_factory=list)
    hazardFragments: list[WeightedTextFragment] = field(default_factory=list)
    affordanceFragments: list[WeightedTextFragment] = field(default_factory=list)
    closingFragments: list[WeightedTextFragment] = field(default_factory=list)
    descriptionPackId: str = ""

    def __post_init__(self):
        self.name = clean_text(self.name)
        self.description = str(self.description or "")
        self.openaiHint = str(self.openaiHint or "")
        self.openingFragments = [entry if isinstance(entry, WeightedTextFragment) else WeightedTextFragment.from_dict(entry) for entry in (self.openingFragments or [])]
        self.landmarkFragments = [entry if isinstance(entry, WeightedTextFragment) else WeightedTextFragment.from_dict(entry) for entry in (self.landmarkFragments or [])]
        self.atmosphereFragments = [entry if isinstance(entry, WeightedTextFragment) else WeightedTextFragment.from_dict(entry) for entry in (self.atmosphereFragments or [])]
        self.hazardFragments = [entry if isinstance(entry, WeightedTextFragment) else WeightedTextFragment.from_dict(entry) for entry in (self.hazardFragments or [])]
        self.affordanceFragments = [entry if isinstance(entry, WeightedTextFragment) else WeightedTextFragment.from_dict(entry) for entry in (self.affordanceFragments or [])]
        self.closingFragments = [entry if isinstance(entry, WeightedTextFragment) else WeightedTextFragment.from_dict(entry) for entry in (self.closingFragments or [])]
        self.descriptionPackId = clean_text(self.descriptionPackId)

    def to_dict(self) -> dict[str, Any]:
        return {
            "descriptionPackId": self.descriptionPackId,
            "name": self.name,
            "description": self.description,
            "openaiHint": self.openaiHint,
            "openingFragments": [entry.to_dict() for entry in self.openingFragments],
            "landmarkFragments": [entry.to_dict() for entry in self.landmarkFragments],
            "atmosphereFragments": [entry.to_dict() for entry in self.atmosphereFragments],
            "hazardFragments": [entry.to_dict() for entry in self.hazardFragments],
            "affordanceFragments": [entry.to_dict() for entry in self.affordanceFragments],
            "closingFragments": [entry.to_dict() for entry in self.closingFragments],
        }

    @classmethod
    def from_dict(cls, data: Any) -> "DescriptionPack":
        if not isinstance(data, dict):
            raise ValueError("Description pack data must be a dictionary.")
        name = clean_text(data.get("name", ""))
        if not name:
            raise ValueError("Description pack data must include a non-empty name.")
        return cls(
            name=name,
            description=str(data.get("description", "") or ""),
            openaiHint=str(data.get("openaiHint", "") or ""),
            openingFragments=data.get("openingFragments", []),
            landmarkFragments=data.get("landmarkFragments", []),
            atmosphereFragments=data.get("atmosphereFragments", []),
            hazardFragments=data.get("hazardFragments", []),
            affordanceFragments=data.get("affordanceFragments", []),
            closingFragments=data.get("closingFragments", []),
            descriptionPackId=clean_text(data.get("descriptionPackId", "")),
        )


@dataclass
class NodeGenerationProfile:
    name: str
    description: str = ""
    rendererMode: SceneDescriptionMode = SceneDescriptionMode.LOCAL_ONLY
    roleWeights: dict[str, float] = field(default_factory=dict)
    minFeatures: int = 1
    maxFeatures: int = 3
    minHooks: int = 0
    maxHooks: int = 2
    antiRepetitionStrength: float = 0.4
    hazardBias: float = 1.0
    affordanceBias: float = 1.0
    hookBias: float = 1.0
    generationProfileId: str = ""

    def __post_init__(self):
        self.name = clean_text(self.name)
        self.description = str(self.description or "")
        self.rendererMode = coerce_enum(SceneDescriptionMode, self.rendererMode, SceneDescriptionMode.LOCAL_ONLY)
        self.roleWeights = normalize_string_map(self.roleWeights)
        self.minFeatures = max(0, int(self.minFeatures or 0))
        self.maxFeatures = max(self.minFeatures, int(self.maxFeatures or self.minFeatures))
        self.minHooks = max(0, int(self.minHooks or 0))
        self.maxHooks = max(self.minHooks, int(self.maxHooks or self.minHooks))
        self.antiRepetitionStrength = max(0.0, min(1.0, float(self.antiRepetitionStrength or 0.0)))
        self.hazardBias = max(0.0, float(self.hazardBias or 0.0))
        self.affordanceBias = max(0.0, float(self.affordanceBias or 0.0))
        self.hookBias = max(0.0, float(self.hookBias or 0.0))
        self.generationProfileId = clean_text(self.generationProfileId)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generationProfileId": self.generationProfileId,
            "name": self.name,
            "description": self.description,
            "rendererMode": self.rendererMode.name,
            "roleWeights": dict(self.roleWeights),
            "minFeatures": int(self.minFeatures),
            "maxFeatures": int(self.maxFeatures),
            "minHooks": int(self.minHooks),
            "maxHooks": int(self.maxHooks),
            "antiRepetitionStrength": float(self.antiRepetitionStrength),
            "hazardBias": float(self.hazardBias),
            "affordanceBias": float(self.affordanceBias),
            "hookBias": float(self.hookBias),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "NodeGenerationProfile":
        if not isinstance(data, dict):
            raise ValueError("Generation profile data must be a dictionary.")
        name = clean_text(data.get("name", ""))
        if not name:
            raise ValueError("Generation profile data must include a non-empty name.")
        return cls(
            name=name,
            description=str(data.get("description", "") or ""),
            rendererMode=data.get("rendererMode", SceneDescriptionMode.LOCAL_ONLY.name),
            roleWeights=data.get("roleWeights", {}),
            minFeatures=int(data.get("minFeatures", 1) or 1),
            maxFeatures=int(data.get("maxFeatures", 3) or 3),
            minHooks=int(data.get("minHooks", 0) or 0),
            maxHooks=int(data.get("maxHooks", 2) or 2),
            antiRepetitionStrength=float(data.get("antiRepetitionStrength", 0.4) or 0.4),
            hazardBias=float(data.get("hazardBias", 1.0) or 1.0),
            affordanceBias=float(data.get("affordanceBias", 1.0) or 1.0),
            hookBias=float(data.get("hookBias", 1.0) or 1.0),
            generationProfileId=clean_text(data.get("generationProfileId", "")),
        )


Biome = BiomeArchetype
Terrain = TerrainProfile
Climate = ClimateProfile
