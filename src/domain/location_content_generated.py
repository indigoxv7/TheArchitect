from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.location_content_common import SceneDescriptionMode, clean_text, coerce_enum, normalize_payload_dict, normalize_string_map, normalize_tag_list, normalize_text_list


@dataclass
class SettingContext:
    biomeId: str
    biomeName: str
    terrainId: str
    terrainName: str
    climateId: str
    climateName: str
    generationProfileId: str = ""
    descriptionPackId: str = ""
    settingContextTags: list[str] = field(default_factory=list)
    civilizationTags: list[str] = field(default_factory=list)
    threatTags: list[str] = field(default_factory=list)
    resourceTags: list[str] = field(default_factory=list)
    mythicTags: list[str] = field(default_factory=list)
    ecologyTags: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.biomeId = clean_text(self.biomeId)
        self.biomeName = clean_text(self.biomeName)
        self.terrainId = clean_text(self.terrainId)
        self.terrainName = clean_text(self.terrainName)
        self.climateId = clean_text(self.climateId)
        self.climateName = clean_text(self.climateName)
        self.generationProfileId = clean_text(self.generationProfileId)
        self.descriptionPackId = clean_text(self.descriptionPackId)
        self.settingContextTags = normalize_tag_list(self.settingContextTags)
        self.civilizationTags = normalize_tag_list(self.civilizationTags)
        self.threatTags = normalize_tag_list(self.threatTags)
        self.resourceTags = normalize_tag_list(self.resourceTags)
        self.mythicTags = normalize_tag_list(self.mythicTags)
        self.ecologyTags = normalize_tag_list(self.ecologyTags)

    @property
    def allTags(self) -> list[str]:
        return normalize_tag_list(
            self.settingContextTags
            + self.civilizationTags
            + self.threatTags
            + self.resourceTags
            + self.mythicTags
            + self.ecologyTags
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "biomeId": self.biomeId,
            "biomeName": self.biomeName,
            "terrainId": self.terrainId,
            "terrainName": self.terrainName,
            "climateId": self.climateId,
            "climateName": self.climateName,
            "generationProfileId": self.generationProfileId,
            "descriptionPackId": self.descriptionPackId,
            "settingContextTags": list(self.settingContextTags),
            "civilizationTags": list(self.civilizationTags),
            "threatTags": list(self.threatTags),
            "resourceTags": list(self.resourceTags),
            "mythicTags": list(self.mythicTags),
            "ecologyTags": list(self.ecologyTags),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "SettingContext":
        if not isinstance(data, dict):
            raise ValueError("Setting context data must be a dictionary.")
        return cls(
            biomeId=data.get("biomeId", ""),
            biomeName=data.get("biomeName", ""),
            terrainId=data.get("terrainId", ""),
            terrainName=data.get("terrainName", ""),
            climateId=data.get("climateId", ""),
            climateName=data.get("climateName", ""),
            generationProfileId=data.get("generationProfileId", ""),
            descriptionPackId=data.get("descriptionPackId", ""),
            settingContextTags=data.get("settingContextTags", []),
            civilizationTags=data.get("civilizationTags", []),
            threatTags=data.get("threatTags", []),
            resourceTags=data.get("resourceTags", []),
            mythicTags=data.get("mythicTags", []),
            ecologyTags=data.get("ecologyTags", []),
        )


@dataclass
class GeneratedFeatureState:
    featureId: str
    name: str
    category: str = "ambient"
    tags: list[str] = field(default_factory=list)
    affordanceTags: list[str] = field(default_factory=list)
    hazardTags: list[str] = field(default_factory=list)
    memoryTags: list[str] = field(default_factory=list)
    visibleTags: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    descriptionHints: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.featureId = clean_text(self.featureId)
        self.name = clean_text(self.name)
        self.category = clean_text(self.category) or "ambient"
        self.tags = normalize_tag_list(self.tags)
        self.affordanceTags = normalize_tag_list(self.affordanceTags)
        self.hazardTags = normalize_tag_list(self.hazardTags)
        self.memoryTags = normalize_tag_list(self.memoryTags)
        self.visibleTags = normalize_tag_list(self.visibleTags)
        self.metrics = normalize_string_map(self.metrics)
        self.payload = normalize_payload_dict(self.payload)
        self.descriptionHints = normalize_text_list(self.descriptionHints)

    def to_dict(self) -> dict[str, Any]:
        return {
            "featureId": self.featureId,
            "name": self.name,
            "category": self.category,
            "tags": list(self.tags),
            "affordanceTags": list(self.affordanceTags),
            "hazardTags": list(self.hazardTags),
            "memoryTags": list(self.memoryTags),
            "visibleTags": list(self.visibleTags),
            "metrics": dict(self.metrics),
            "payload": dict(self.payload),
            "descriptionHints": list(self.descriptionHints),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "GeneratedFeatureState":
        if not isinstance(data, dict):
            raise ValueError("Generated feature data must be a dictionary.")
        return cls(
            featureId=data.get("featureId", ""),
            name=data.get("name", ""),
            category=data.get("category", "ambient"),
            tags=data.get("tags", []),
            affordanceTags=data.get("affordanceTags", []),
            hazardTags=data.get("hazardTags", []),
            memoryTags=data.get("memoryTags", []),
            visibleTags=data.get("visibleTags", []),
            metrics=data.get("metrics", {}),
            payload=data.get("payload", {}),
            descriptionHints=data.get("descriptionHints", []),
        )


@dataclass
class GeneratedHookState:
    hookId: str
    name: str
    hookType: str = ""
    tags: list[str] = field(default_factory=list)
    memoryTags: list[str] = field(default_factory=list)
    visibleText: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.hookId = clean_text(self.hookId)
        self.name = clean_text(self.name)
        self.hookType = clean_text(self.hookType)
        self.tags = normalize_tag_list(self.tags)
        self.memoryTags = normalize_tag_list(self.memoryTags)
        self.visibleText = str(self.visibleText or "")
        self.payload = normalize_payload_dict(self.payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hookId": self.hookId,
            "name": self.name,
            "hookType": self.hookType,
            "tags": list(self.tags),
            "memoryTags": list(self.memoryTags),
            "visibleText": self.visibleText,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "GeneratedHookState":
        if not isinstance(data, dict):
            raise ValueError("Generated hook data must be a dictionary.")
        return cls(
            hookId=data.get("hookId", ""),
            name=data.get("name", ""),
            hookType=data.get("hookType", ""),
            tags=data.get("tags", []),
            memoryTags=data.get("memoryTags", []),
            visibleText=data.get("visibleText", ""),
            payload=data.get("payload", {}),
        )


@dataclass
class GeneratedNodeContent:
    nodeId: int
    sceneDisplayName: str = ""
    battleTerrainLabel: str = ""
    roleId: str = ""
    roleName: str = ""
    roleTags: list[str] = field(default_factory=list)
    settingContextTags: list[str] = field(default_factory=list)
    featureTags: list[str] = field(default_factory=list)
    affordanceTags: list[str] = field(default_factory=list)
    hazardTags: list[str] = field(default_factory=list)
    hookTags: list[str] = field(default_factory=list)
    memoryTags: list[str] = field(default_factory=list)
    canonicalTags: list[str] = field(default_factory=list)
    featureStates: list[GeneratedFeatureState] = field(default_factory=list)
    hookStates: list[GeneratedHookState] = field(default_factory=list)
    visibleSummaryLines: list[str] = field(default_factory=list)
    localDescription: str = ""
    openAIDescription: str = ""

    def __post_init__(self):
        self.nodeId = int(self.nodeId)
        self.sceneDisplayName = str(self.sceneDisplayName or "")
        self.battleTerrainLabel = str(self.battleTerrainLabel or "")
        self.roleId = clean_text(self.roleId)
        self.roleName = clean_text(self.roleName)
        self.roleTags = normalize_tag_list(self.roleTags)
        self.settingContextTags = normalize_tag_list(self.settingContextTags)
        self.featureTags = normalize_tag_list(self.featureTags)
        self.affordanceTags = normalize_tag_list(self.affordanceTags)
        self.hazardTags = normalize_tag_list(self.hazardTags)
        self.hookTags = normalize_tag_list(self.hookTags)
        self.memoryTags = normalize_tag_list(self.memoryTags)
        self.canonicalTags = normalize_tag_list(self.canonicalTags)
        self.featureStates = [entry if isinstance(entry, GeneratedFeatureState) else GeneratedFeatureState.from_dict(entry) for entry in (self.featureStates or []) if entry is not None]
        self.hookStates = [entry if isinstance(entry, GeneratedHookState) else GeneratedHookState.from_dict(entry) for entry in (self.hookStates or []) if entry is not None]
        self.visibleSummaryLines = normalize_text_list(self.visibleSummaryLines)
        self.localDescription = str(self.localDescription or "")
        self.openAIDescription = str(self.openAIDescription or "")

    def preferred_description(self, renderer_mode: SceneDescriptionMode | str | None = None) -> str:
        mode = coerce_enum(SceneDescriptionMode, renderer_mode, SceneDescriptionMode.LOCAL_ONLY)
        if mode == SceneDescriptionMode.OPENAI_ONLY and self.openAIDescription:
            return self.openAIDescription
        if mode == SceneDescriptionMode.LOCAL_PRIMARY_OPENAI_CACHE:
            return self.localDescription or self.openAIDescription
        if mode == SceneDescriptionMode.LOCAL_ONLY:
            return self.localDescription or self.openAIDescription
        return self.localDescription or self.openAIDescription

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodeId": int(self.nodeId),
            "sceneDisplayName": self.sceneDisplayName,
            "battleTerrainLabel": self.battleTerrainLabel,
            "roleId": self.roleId,
            "roleName": self.roleName,
            "roleTags": list(self.roleTags),
            "settingContextTags": list(self.settingContextTags),
            "featureTags": list(self.featureTags),
            "affordanceTags": list(self.affordanceTags),
            "hazardTags": list(self.hazardTags),
            "hookTags": list(self.hookTags),
            "memoryTags": list(self.memoryTags),
            "canonicalTags": list(self.canonicalTags),
            "featureStates": [entry.to_dict() for entry in self.featureStates],
            "hookStates": [entry.to_dict() for entry in self.hookStates],
            "visibleSummaryLines": list(self.visibleSummaryLines),
            "localDescription": self.localDescription,
            "openAIDescription": self.openAIDescription,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "GeneratedNodeContent":
        if not isinstance(data, dict):
            raise ValueError("Generated node content data must be a dictionary.")
        return cls(
            nodeId=int(data.get("nodeId", 0) or 0),
            sceneDisplayName=data.get("sceneDisplayName", ""),
            battleTerrainLabel=data.get("battleTerrainLabel", ""),
            roleId=data.get("roleId", ""),
            roleName=data.get("roleName", ""),
            roleTags=data.get("roleTags", []),
            settingContextTags=data.get("settingContextTags", []),
            featureTags=data.get("featureTags", []),
            affordanceTags=data.get("affordanceTags", []),
            hazardTags=data.get("hazardTags", []),
            hookTags=data.get("hookTags", []),
            memoryTags=data.get("memoryTags", []),
            canonicalTags=data.get("canonicalTags", []),
            featureStates=data.get("featureStates", []),
            hookStates=data.get("hookStates", []),
            visibleSummaryLines=data.get("visibleSummaryLines", []),
            localDescription=data.get("localDescription", ""),
            openAIDescription=data.get("openAIDescription", ""),
        )
