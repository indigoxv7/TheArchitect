import re
from typing import Any

from src.domain.location_content import (
    BiomeArchetype,
    ClimateProfile,
    CompatibilitySelectionMode,
    DescriptionPack,
    EnvironmentEffect,
    FeatureTemplate,
    HookTemplate,
    NodeGenerationProfile,
    NodeRoleTemplate,
    SceneDescriptionMode,
    TerrainProfile,
)
from src.persistence.environmentbook_store import EnvironmentbookStore
from src.services.game_context import GameContext


class EnvironmentService:
    CATALOGS = {
        "effects": ("all_environment_effects", EnvironmentEffect, "effectId", "Effect"),
        "terrains": ("all_terrains", TerrainProfile, "terrainId", "Terrain"),
        "climates": ("all_climates", ClimateProfile, "climateId", "Climate"),
        "biomes": ("all_biomes", BiomeArchetype, "biomeId", "Biome"),
        "node_roles": ("all_node_roles", NodeRoleTemplate, "roleId", "Role"),
        "features": ("all_feature_templates", FeatureTemplate, "featureId", "Feature"),
        "hooks": ("all_hook_templates", HookTemplate, "hookId", "Hook"),
        "description_packs": ("all_description_packs", DescriptionPack, "descriptionPackId", "DescriptionPack"),
        "generation_profiles": (
            "all_generation_profiles",
            NodeGenerationProfile,
            "generationProfileId",
            "GenerationProfile",
        ),
    }

    def __init__(self, environmentbook_path: str, context: GameContext):
        self.context = context
        self.store = EnvironmentbookStore(environmentbook_path)
        self._ensure_context_fields()

    def _ensure_context_fields(self):
        for attribute_name, _cls, _id_attr, _fallback in self.CATALOGS.values():
            if not hasattr(self.context, attribute_name):
                setattr(self.context, attribute_name, {})
        for overview_name in (
            "effectbook_overview",
            "terrainbook_overview",
            "climatebook_overview",
            "biomebook_overview",
            "node_rolebook_overview",
            "featurebook_overview",
            "hookbook_overview",
            "description_packbook_overview",
            "generation_profilebook_overview",
        ):
            if not hasattr(self.context, overview_name):
                setattr(self.context, overview_name, "")

    @staticmethod
    def _slugify_name(name: str, fallback: str) -> str:
        compact = re.sub(r"\s+", "", str(name or "").strip())
        compact = re.sub(r"[^A-Za-z0-9_\-]", "", compact)
        return compact or fallback

    def _catalog_storage(self, catalog_key: str) -> dict[str, object]:
        attribute_name = self.CATALOGS[catalog_key][0]
        storage = getattr(self.context, attribute_name, None)
        if not isinstance(storage, dict):
            storage = {}
            setattr(self.context, attribute_name, storage)
        return storage

    def _catalog_id_attr(self, catalog_key: str) -> str:
        return self.CATALOGS[catalog_key][2]

    def _generate_id(self, catalog_key: str, name: str) -> str:
        storage = self._catalog_storage(catalog_key)
        fallback = self.CATALOGS[catalog_key][3]
        prefix = self._slugify_name(name, fallback)
        index = len(storage)
        candidate = f"{prefix}{index}"
        while candidate in storage:
            index += 1
            candidate = f"{prefix}{index}"
        return candidate

    @staticmethod
    def _parse_label_id(label: str) -> str:
        text = str(label or "").strip()
        if text.endswith("]") and "[" in text:
            return text[text.rfind("[") + 1 : -1].strip()
        return text

    def _list_catalog(self, catalog_key: str) -> list[object]:
        storage = self._catalog_storage(catalog_key)
        id_attr = self._catalog_id_attr(catalog_key)
        return sorted(storage.values(), key=lambda entry: (str(getattr(entry, "name", "") or "").lower(), str(getattr(entry, id_attr, "") or "")))

    def _get_by_id(self, catalog_key: str, identifier: str):
        return self._catalog_storage(catalog_key).get(str(identifier or "").strip())

    def _get_by_identifier(self, catalog_key: str, identifier: str):
        key = str(identifier or "").strip()
        if not key:
            return None
        direct = self._get_by_id(catalog_key, key)
        if direct is not None:
            return direct
        matches = [entry for entry in self._list_catalog(catalog_key) if str(getattr(entry, "name", "") or "").lower() == key.lower()]
        return matches[0] if len(matches) == 1 else None

    def _create_from_dict(self, catalog_key: str, data: dict):
        cls = self.CATALOGS[catalog_key][1]
        id_attr = self._catalog_id_attr(catalog_key)
        entry = cls.from_dict(data)
        self._validate_entry(catalog_key, entry)
        storage = self._catalog_storage(catalog_key)
        current_id = str(getattr(entry, id_attr, "") or "").strip()
        if not current_id:
            setattr(entry, id_attr, self._generate_id(catalog_key, str(getattr(entry, "name", "") or "")))
            current_id = str(getattr(entry, id_attr, "") or "")
        if current_id in storage:
            raise ValueError(f"{catalog_key} ID '{current_id}' already exists.")
        storage[current_id] = entry
        self.save_environmentbook()
        return entry

    def _edit_from_patch(self, catalog_key: str, identifier: str, patch: dict):
        existing = self._get_by_identifier(catalog_key, identifier)
        if existing is None:
            raise ValueError(f"{catalog_key} '{identifier}' does not exist or is ambiguous.")
        id_attr = self._catalog_id_attr(catalog_key)
        merged = existing.to_dict()
        merged.update(patch or {})
        merged[id_attr] = getattr(existing, id_attr)
        if not str(merged.get("name", "") or "").strip():
            merged["name"] = getattr(existing, "name", "")
        cls = self.CATALOGS[catalog_key][1]
        updated = cls.from_dict(merged)
        setattr(updated, id_attr, getattr(existing, id_attr))
        self._validate_entry(catalog_key, updated)
        self._catalog_storage(catalog_key)[getattr(updated, id_attr)] = updated
        self.save_environmentbook()
        return updated

    def _validate_effect_refs(self, effect_ids: list[str]):
        for effect_id in effect_ids:
            if self.get_effect_by_id(effect_id) is None:
                raise ValueError(f"Effect '{effect_id}' does not exist.")

    def _validate_biome(self, biome: BiomeArchetype):
        self._validate_effect_refs(getattr(biome, "effectIds", []))
        for terrain_id in list(biome.compatibleTerrainIds) + list(biome.incompatibleTerrainIds):
            if self.get_terrain_by_id(terrain_id) is None:
                raise ValueError(f"Terrain '{terrain_id}' does not exist.")
        for climate_id in list(biome.compatibleClimateIds) + list(biome.incompatibleClimateIds):
            if self.get_climate_by_id(climate_id) is None:
                raise ValueError(f"Climate '{climate_id}' does not exist.")

    def _validate_entry(self, catalog_key: str, entry):
        if catalog_key in {"terrains", "climates", "biomes"}:
            self._validate_effect_refs(list(getattr(entry, "effectIds", [])))
        if catalog_key == "biomes":
            self._validate_biome(entry)

    def load_environmentbook(self):
        payload = self.store.load()
        self._ensure_context_fields()
        for catalog_key in self.CATALOGS:
            self._catalog_storage(catalog_key).clear()

        migrated = False
        for catalog_key, (_attribute_name, cls, id_attr, _fallback) in self.CATALOGS.items():
            for raw_entry in payload.get(catalog_key, []) or []:
                try:
                    entry = cls.from_dict(raw_entry)
                    self._validate_entry(catalog_key, entry)
                except Exception:
                    continue
                entry_id = str(getattr(entry, id_attr, "") or "").strip()
                if not entry_id or entry_id in self._catalog_storage(catalog_key):
                    setattr(entry, id_attr, self._generate_id(catalog_key, str(getattr(entry, "name", "") or "")))
                    migrated = True
                    entry_id = str(getattr(entry, id_attr, "") or "")
                self._catalog_storage(catalog_key)[entry_id] = entry

        if not self.list_biomes() or not self.list_node_roles() or not self.list_description_packs() or not self.list_generation_profiles():
            self._seed_defaults(clear_existing=(not any(self._catalog_storage(key) for key in self.CATALOGS)))
            migrated = True

        if self._ensure_builtin_aliases():
            migrated = True

        self._refresh_overviews()
        if migrated:
            self.save_environmentbook()

    def _ensure_builtin_aliases(self) -> bool:
        changed = False
        biome_storage = self._catalog_storage("biomes")
        if "Jungle0" not in biome_storage:
            biome_storage["Jungle0"] = BiomeArchetype(
                name="Jungle",
                description="Dense, humid growth full of layered cover, territorial signs, and hidden movement lanes.",
                terrainCompatibilityMode=CompatibilitySelectionMode.SELECTED,
                compatibleTerrainIds=["OvergrownPaths0", "FloodedHollow0"],
                terrainIncompatibilityMode="ALL_EXCEPT_COMPATIBLE",
                climateCompatibilityMode=CompatibilitySelectionMode.SELECTED,
                compatibleClimateIds=["HotHumid0", "StormWet0"],
                climateIncompatibilityMode="ALL_EXCEPT_COMPATIBLE",
                canonicalBaseTags=["jungle", "frontier"],
                civilizationPriors=["encroaching_outposts"],
                threatPriors=["ambush_predators", "skirmishers"],
                resourcePriors=["rare_herbs", "fungal_growth"],
                mythicPriors=["old_spirits"],
                ecologyPriors=["canopy", "undergrowth"],
                biomeId="Jungle0",
            )
            changed = True
        return changed

    def save_environmentbook(self):
        payload = {"format_version": 2}
        for catalog_key in self.CATALOGS:
            payload[catalog_key] = [entry.to_dict() for entry in self._list_catalog(catalog_key)]
        self.store.save(payload)
        self._refresh_overviews()

    def _seed_defaults(self, clear_existing: bool = False):
        if clear_existing:
            for catalog_key in self.CATALOGS:
                self._catalog_storage(catalog_key).clear()

        for effect in []:
            self._catalog_storage("effects")[effect.effectId] = effect

        terrain_entries = [
            TerrainProfile(name="Overgrown Paths", description="Dense undergrowth and root-choked trails.", canonicalTags=["overgrown", "pathways"], traversalTags=["slow_travel"], visibilityTags=["broken_sightlines"], obstacleTags=["roots", "vines"], terrainId="OvergrownPaths0"),
            TerrainProfile(name="Ruined Foundations", description="Broken masonry and half-swallowed walls.", canonicalTags=["ruins", "masonry"], landformTags=["collapsed_structures"], traversalTags=["uneven_footing"], visibilityTags=["partial_cover"], terrainId="RuinedFoundations0"),
            TerrainProfile(name="Flooded Hollow", description="Standing water, soft mud, and blackwater channels.", canonicalTags=["flooded", "marsh"], wetnessTags=["waterlogged"], traversalTags=["careful_footing"], obstacleTags=["sinking_ground"], terrainId="FloodedHollow0"),
        ]
        climate_entries = [
            ClimateProfile(name="Temperate Mist", temperature="Mild", humidity="Damp", description="Cool air and ground-hugging mist.", canonicalTags=["temperate", "misty"], weatherTags=["drizzle"], fogTags=["low_fog"], climateId="TemperateMist0"),
            ClimateProfile(name="Hot Humid", temperature="Hot", humidity="Humid", description="Oppressive heat and wet air.", canonicalTags=["hot", "humid"], weatherTags=["steam_haze"], climateId="HotHumid0"),
            ClimateProfile(name="Storm-Wet", temperature="Warm", humidity="Saturated", description="Frequent storms and pooling runoff.", canonicalTags=["storm_touched", "wet"], weatherTags=["thunder"], floodTags=["flash_flood"], climateId="StormWet0"),
        ]
        biome_entries = [
            BiomeArchetype(name="Wilderness", description="Untamed territory shaped by ecology more than civilization.", canonicalBaseTags=["wildlands"], civilizationPriors=["frontier"], threatPriors=["predators"], resourcePriors=["forage"], ecologyPriors=["dense_growth"], biomeId="Wilderness0"),
            BiomeArchetype(name="Jungle Frontier", description="Aggressive plant life, territorial inhabitants, and wet heat.", terrainCompatibilityMode=CompatibilitySelectionMode.SELECTED, compatibleTerrainIds=["OvergrownPaths0", "FloodedHollow0"], terrainIncompatibilityMode="ALL_EXCEPT_COMPATIBLE", climateCompatibilityMode=CompatibilitySelectionMode.SELECTED, compatibleClimateIds=["HotHumid0", "StormWet0"], climateIncompatibilityMode="ALL_EXCEPT_COMPATIBLE", canonicalBaseTags=["jungle", "frontier"], civilizationPriors=["encroaching_outposts"], threatPriors=["ambush_predators", "skirmishers"], resourcePriors=["rare_herbs", "fungal_growth"], mythicPriors=["old_spirits"], ecologyPriors=["canopy", "undergrowth"], biomeId="JungleFrontier0"),
            BiomeArchetype(name="Jungle", description="Dense, humid growth full of layered cover, territorial signs, and hidden movement lanes.", terrainCompatibilityMode=CompatibilitySelectionMode.SELECTED, compatibleTerrainIds=["OvergrownPaths0", "FloodedHollow0"], terrainIncompatibilityMode="ALL_EXCEPT_COMPATIBLE", climateCompatibilityMode=CompatibilitySelectionMode.SELECTED, compatibleClimateIds=["HotHumid0", "StormWet0"], climateIncompatibilityMode="ALL_EXCEPT_COMPATIBLE", canonicalBaseTags=["jungle", "frontier"], civilizationPriors=["encroaching_outposts"], threatPriors=["ambush_predators", "skirmishers"], resourcePriors=["rare_herbs", "fungal_growth"], mythicPriors=["old_spirits"], ecologyPriors=["canopy", "undergrowth"], biomeId="Jungle0"),
            BiomeArchetype(name="Overrun Ruins", description="A broken site where nature and old stone compete for control.", terrainCompatibilityMode=CompatibilitySelectionMode.SELECTED, compatibleTerrainIds=["RuinedFoundations0", "OvergrownPaths0"], terrainIncompatibilityMode="ALL_EXCEPT_COMPATIBLE", canonicalBaseTags=["ruins", "reclamation"], civilizationPriors=["abandoned_structures"], threatPriors=["scavengers"], resourcePriors=["salvage"], mythicPriors=["forgotten_rites"], ecologyPriors=["reclaimed_stone"], biomeId="OverrunRuins0"),
        ]
        role_entries = [
            NodeRoleTemplate(name="Landmark", description="A visually distinctive place that anchors orientation.", roleTags=["landmark", "discovery"], desiredAffordanceTags=["observe", "survey"], minFeatures=1, maxFeatures=3, roleId="Landmark0"),
            NodeRoleTemplate(name="Ambush Corridor", description="A tense approach where hostiles can control the flow of movement.", roleTags=["ambush", "tension"], desiredHazardTags=["exposed", "chokepoint"], desiredHookTypes=["Encounter", "Clue"], minFeatures=2, maxFeatures=3, roleId="AmbushCorridor0"),
            NodeRoleTemplate(name="Resource Stop", description="A node defined by useful supplies or recoverable valuables.", roleTags=["resource", "opportunity"], desiredAffordanceTags=["forage", "loot"], desiredHookTypes=["Treasure"], minFeatures=1, maxFeatures=2, roleId="ResourceStop0"),
            NodeRoleTemplate(name="Lore Reveal", description="A place that hints at history, danger, or a missing story thread.", roleTags=["lore", "mystery"], desiredHookTypes=["Lore", "Clue", "Quest Seed"], minFeatures=1, maxFeatures=3, roleId="LoreReveal0"),
            NodeRoleTemplate(name="Traversal Puzzle", description="Movement through the node is the main challenge.", roleTags=["traversal", "challenge"], desiredAffordanceTags=["climb", "cross", "sneak"], desiredHazardTags=["fall_risk", "unstable_ground"], minFeatures=2, maxFeatures=3, roleId="TraversalPuzzle0"),
            NodeRoleTemplate(name="Safe Pocket", description="A relatively calm place that offers a breath between risks.", roleTags=["relief", "shelter"], desiredAffordanceTags=["rest", "regroup"], minFeatures=1, maxFeatures=2, roleId="SafePocket0"),
        ]
        feature_entries = [
            FeatureTemplate(name="Ruined Watchtower", category="structure", description="A broken elevated post with good sightlines.", tags=["watchtower", "ruins"], affordanceTags=["observe", "high_ground"], hazardTags=["rotting_supports"], memoryTags=["watchtower"], visibleTags=["tower"], localDescriptionHints=["a ruined watchtower leans above the node"], featureId="RuinedWatchtower0"),
            FeatureTemplate(name="Blackwater Stream", category="hydrology", description="Dark water cuts through the area.", tags=["stream", "blackwater"], affordanceTags=["drink_if_filtered", "cross"], hazardTags=["slippery_bank"], memoryTags=["stream"], visibleTags=["water"], localDescriptionHints=["a blackwater stream threads through the ground"], featureId="BlackwaterStream0"),
            FeatureTemplate(name="Totem Markers", category="faction_sign", description="Claim markers or warnings left by locals.", tags=["totem_markers", "territory"], hazardTags=["territorial_response"], memoryTags=["warning_signs"], visibleTags=["markers"], localDescriptionHints=["totem markers warn that someone claims this place"], featureId="TotemMarkers0"),
            FeatureTemplate(name="Supply Cache", category="resource", description="A stash or crate hidden behind cover.", tags=["cache", "supplies"], affordanceTags=["loot"], memoryTags=["supplies"], visibleTags=["cache"], hookTypeSuggestions=["Treasure"], localDescriptionHints=["someone cached supplies here not long ago"], featureId="SupplyCache0"),
            FeatureTemplate(name="Thorn Curtain", category="flora", description="Dense thorn growth narrows movement.", tags=["thorns", "dense_growth"], hazardTags=["scrapes", "slow_travel"], affordanceTags=["hide"], memoryTags=["thorns"], visibleTags=["thorns"], localDescriptionHints=["thorny growth closes in around the route"], featureId="ThornCurtain0"),
            FeatureTemplate(name="Broken Bridge", category="traversal", description="A collapsed crossing that still tempts passage.", tags=["broken_bridge", "gap"], affordanceTags=["cross", "climb"], hazardTags=["fall_risk"], memoryTags=["bridge"], visibleTags=["bridge"], localDescriptionHints=["a broken bridge leaves an awkward crossing"], featureId="BrokenBridge0"),
            FeatureTemplate(name="Fungus Lanterns", category="flora", description="Soft glow from strange fungus clusters.", tags=["bioluminescent", "fungal"], affordanceTags=["see_in_dark"], memoryTags=["glowing_fungus"], visibleTags=["glow"], localDescriptionHints=["pale fungus lends the node an eerie light"], featureId="FungusLanterns0"),
            FeatureTemplate(name="Predator Spoor", category="fauna_sign", description="Fresh signs that something territorial passed through.", tags=["tracks", "predator_sign"], hazardTags=["ambush_risk"], memoryTags=["tracks"], visibleTags=["tracks"], hookTypeSuggestions=["Clue", "Encounter"], localDescriptionHints=["fresh spoor suggests a predator patrols nearby"], featureId="PredatorSpoor0"),
        ]
        hook_entries = [
            HookTemplate(name="Fresh Tracks", hookType="CLUE", description="A clue that points toward nearby occupants.", tags=["tracks", "clue"], memoryTags=["clue"], visibleText="Fresh tracks point deeper into the mission area.", payload={"kind": "clue"}, hookId="FreshTracks0"),
            HookTemplate(name="Hidden Nano Stash", hookType="TREASURE", description="A concealed stash of Nano.", tags=["treasure", "nano"], memoryTags=["treasure"], visibleText="Something valuable is tucked out of sight here.", payload={"kind": "treasure"}, hookId="HiddenNanoStash0"),
            HookTemplate(name="Rival Patrol Signs", hookType="ENCOUNTER", description="Signs of a hostile group controlling the area.", tags=["hostile_presence", "patrol"], memoryTags=["hostiles"], visibleText="The place shows clear signs of hostile control.", payload={"kind": "encounter"}, hookId="RivalPatrolSigns0"),
            HookTemplate(name="Forgotten Shrine Murals", hookType="LORE", description="Fragments of old meaning on surviving surfaces.", tags=["lore", "murals"], memoryTags=["lore"], visibleText="Faded markings suggest a story worth studying.", payload={"kind": "lore"}, hookId="ForgottenShrineMurals0"),
        ]
        description_entries = [
            DescriptionPack(name="Default Arrival", description="Balanced local grammar fragments for mission node arrival text.", openaiHint="Describe what the squad notices first on arrival, keep it short and concrete.", openingFragments=[{"text": "The squad arrives in #terrain#, where #climate# hangs over everything."}, {"text": "#biome# closes in around the node, shaped by #terrain# and #climate#."}], landmarkFragments=[{"text": "Most striking is #landmark#."}, {"text": "At a glance, #landmark# defines the scene."}], atmosphereFragments=[{"text": "The area feels #role_mood#, with signs of #feature_list#."}, {"text": "Everything about the node suggests #role_mood# and #feature_list#."}], hazardFragments=[{"text": "The main immediate risk is #hazard#."}], affordanceFragments=[{"text": "It also looks like a place to #affordance#."}], closingFragments=[{"text": "Whatever happened here, it still feels active."}, {"text": "The node invites a closer look, but not a careless one."}], descriptionPackId="DefaultArrival0"),
        ]
        profile_entries = [
            NodeGenerationProfile(name="Balanced Local", description="Default structured generation tuned for local descriptions first.", rendererMode=SceneDescriptionMode.LOCAL_PRIMARY_OPENAI_CACHE, localRendererKey="ollama:qwen3:8b", roleWeights={"Landmark0": 1.0, "AmbushCorridor0": 1.0, "ResourceStop0": 0.9, "LoreReveal0": 0.9, "TraversalPuzzle0": 0.8, "SafePocket0": 0.6}, minFeatures=1, maxFeatures=3, minHooks=0, maxHooks=2, antiRepetitionStrength=0.5, generationProfileId="BalancedLocal0"),
        ]
        for catalog_key, entries in {
            "terrains": terrain_entries,
            "climates": climate_entries,
            "biomes": biome_entries,
            "node_roles": role_entries,
            "features": feature_entries,
            "hooks": hook_entries,
            "description_packs": description_entries,
            "generation_profiles": profile_entries,
        }.items():
            storage = self._catalog_storage(catalog_key)
            id_attr = self._catalog_id_attr(catalog_key)
            for entry in entries:
                storage[str(getattr(entry, id_attr))] = entry

    def _refresh_overviews(self):
        self.context.effectbook_overview = self.build_effect_overview()
        self.context.terrainbook_overview = self.build_terrain_overview()
        self.context.climatebook_overview = self.build_climate_overview()
        self.context.biomebook_overview = self.build_biome_overview()
        self.context.node_rolebook_overview = self._build_overview("node_roles", "node roles")
        self.context.featurebook_overview = self._build_overview("features", "features")
        self.context.hookbook_overview = self._build_overview("hooks", "hooks")
        self.context.description_packbook_overview = self._build_overview("description_packs", "description packs")
        self.context.generation_profilebook_overview = self._build_overview("generation_profiles", "generation profiles")

    def _build_overview(self, catalog_key: str, label: str, max_lines: int = 20) -> str:
        entries = self._list_catalog(catalog_key)
        if not entries:
            return f"No {label} yet."
        lines = [f"- {getattr(entry, 'name', 'Entry')} [{getattr(entry, self._catalog_id_attr(catalog_key), '')}]" for entry in entries[:max_lines]]
        if len(entries) > max_lines:
            lines.append(f"... and {len(entries) - max_lines} more")
        return "\n".join(lines)

    def get_effect_label(self, effect: EnvironmentEffect) -> str:
        return f"{effect.name} [{effect.effectId}]"

    def get_terrain_label(self, terrain: TerrainProfile) -> str:
        return f"{terrain.name} [{terrain.terrainId}]"

    def get_climate_label(self, climate: ClimateProfile) -> str:
        summary = f"{climate.temperature or 'Any Temp'} / {climate.humidity or 'Any Humidity'}"
        return f"{climate.name} [{climate.climateId}] ({summary})"

    def get_biome_label(self, biome: BiomeArchetype) -> str:
        return f"{biome.name} [{biome.biomeId}]"

    def get_node_role_label(self, role: NodeRoleTemplate) -> str:
        return f"{role.name} [{role.roleId}]"

    def get_feature_label(self, feature: FeatureTemplate) -> str:
        return f"{feature.name} [{feature.featureId}] ({feature.category})"

    def get_hook_label(self, hook: HookTemplate) -> str:
        return f"{hook.name} [{hook.hookId}] ({hook.hookType.value})"

    def get_description_pack_label(self, pack: DescriptionPack) -> str:
        return f"{pack.name} [{pack.descriptionPackId}]"

    def get_generation_profile_label(self, profile: NodeGenerationProfile) -> str:
        return f"{profile.name} [{profile.generationProfileId}] ({profile.rendererMode.name})"

    def list_effects(self) -> list[EnvironmentEffect]:
        return self._list_catalog("effects")

    def list_terrains(self) -> list[TerrainProfile]:
        return self._list_catalog("terrains")

    def list_climates(self) -> list[ClimateProfile]:
        return self._list_catalog("climates")

    def list_biomes(self) -> list[BiomeArchetype]:
        return self._list_catalog("biomes")

    def list_node_roles(self) -> list[NodeRoleTemplate]:
        return self._list_catalog("node_roles")

    def list_feature_templates(self) -> list[FeatureTemplate]:
        return self._list_catalog("features")

    def list_hook_templates(self) -> list[HookTemplate]:
        return self._list_catalog("hooks")

    def list_description_packs(self) -> list[DescriptionPack]:
        return self._list_catalog("description_packs")

    def list_generation_profiles(self) -> list[NodeGenerationProfile]:
        return self._list_catalog("generation_profiles")

    def get_effect_by_id(self, effect_id: str) -> EnvironmentEffect | None:
        return self._get_by_id("effects", effect_id)

    def get_terrain_by_id(self, terrain_id: str) -> TerrainProfile | None:
        return self._get_by_id("terrains", terrain_id)

    def get_climate_by_id(self, climate_id: str) -> ClimateProfile | None:
        return self._get_by_id("climates", climate_id)

    def get_biome_by_id(self, biome_id: str) -> BiomeArchetype | None:
        return self._get_by_id("biomes", biome_id)

    def get_node_role_by_id(self, role_id: str) -> NodeRoleTemplate | None:
        return self._get_by_id("node_roles", role_id)

    def get_feature_template_by_id(self, feature_id: str) -> FeatureTemplate | None:
        return self._get_by_id("features", feature_id)

    def get_hook_template_by_id(self, hook_id: str) -> HookTemplate | None:
        return self._get_by_id("hooks", hook_id)

    def get_description_pack_by_id(self, description_pack_id: str) -> DescriptionPack | None:
        return self._get_by_id("description_packs", description_pack_id)

    def get_generation_profile_by_id(self, generation_profile_id: str) -> NodeGenerationProfile | None:
        return self._get_by_id("generation_profiles", generation_profile_id)

    def get_effect(self, identifier: str) -> EnvironmentEffect | None:
        return self._get_by_identifier("effects", identifier)

    def get_terrain(self, identifier: str) -> TerrainProfile | None:
        return self._get_by_identifier("terrains", identifier)

    def get_climate(self, identifier: str) -> ClimateProfile | None:
        return self._get_by_identifier("climates", identifier)

    def get_biome(self, identifier: str) -> BiomeArchetype | None:
        return self._get_by_identifier("biomes", identifier)

    def create_effect_from_dict(self, data: dict): return self._create_from_dict("effects", data)
    def create_terrain_from_dict(self, data: dict): return self._create_from_dict("terrains", data)
    def create_climate_from_dict(self, data: dict): return self._create_from_dict("climates", data)
    def create_biome_from_dict(self, data: dict): return self._create_from_dict("biomes", data)
    def create_node_role_from_dict(self, data: dict): return self._create_from_dict("node_roles", data)
    def create_feature_template_from_dict(self, data: dict): return self._create_from_dict("features", data)
    def create_hook_template_from_dict(self, data: dict): return self._create_from_dict("hooks", data)
    def create_description_pack_from_dict(self, data: dict): return self._create_from_dict("description_packs", data)
    def create_generation_profile_from_dict(self, data: dict): return self._create_from_dict("generation_profiles", data)

    def edit_effect_from_patch(self, identifier: str, patch: dict): return self._edit_from_patch("effects", identifier, patch)
    def edit_terrain_from_patch(self, identifier: str, patch: dict): return self._edit_from_patch("terrains", identifier, patch)
    def edit_climate_from_patch(self, identifier: str, patch: dict): return self._edit_from_patch("climates", identifier, patch)
    def edit_biome_from_patch(self, identifier: str, patch: dict): return self._edit_from_patch("biomes", identifier, patch)
    def edit_node_role_from_patch(self, identifier: str, patch: dict): return self._edit_from_patch("node_roles", identifier, patch)
    def edit_feature_template_from_patch(self, identifier: str, patch: dict): return self._edit_from_patch("features", identifier, patch)
    def edit_hook_template_from_patch(self, identifier: str, patch: dict): return self._edit_from_patch("hooks", identifier, patch)
    def edit_description_pack_from_patch(self, identifier: str, patch: dict): return self._edit_from_patch("description_packs", identifier, patch)
    def edit_generation_profile_from_patch(self, identifier: str, patch: dict): return self._edit_from_patch("generation_profiles", identifier, patch)

    def build_effect_overview(self, max_lines: int = 20) -> str:
        return self._build_overview("effects", "effects", max_lines=max_lines)

    def build_terrain_overview(self, max_lines: int = 20) -> str:
        return self._build_overview("terrains", "terrains", max_lines=max_lines)

    def build_climate_overview(self, max_lines: int = 20) -> str:
        return self._build_overview("climates", "climates", max_lines=max_lines)

    def build_biome_overview(self, max_lines: int = 20) -> str:
        return self._build_overview("biomes", "biomes", max_lines=max_lines)

    def get_default_description_pack(self) -> DescriptionPack | None:
        packs = self.list_description_packs()
        return packs[0] if packs else None

    def get_default_generation_profile(self) -> NodeGenerationProfile | None:
        profiles = self.list_generation_profiles()
        return profiles[0] if profiles else None

    def terrain_candidates_for_biome(self, biome_id: str, override_ids: list[str] | None = None) -> list[TerrainProfile]:
        override_ids = [str(entry or "").strip() for entry in (override_ids or []) if str(entry or "").strip()]
        if override_ids:
            return [terrain for terrain_id in override_ids if (terrain := self.get_terrain_by_id(terrain_id)) is not None]
        biome = self.get_biome_by_id(biome_id)
        terrains = self.list_terrains()
        if biome is None:
            return terrains
        filtered = [terrain for terrain in terrains if biome.allows_terrain(terrain.terrainId)]
        return filtered or terrains

    def climate_candidates_for_biome(self, biome_id: str, override_ids: list[str] | None = None) -> list[ClimateProfile]:
        override_ids = [str(entry or "").strip() for entry in (override_ids or []) if str(entry or "").strip()]
        if override_ids:
            return [climate for climate_id in override_ids if (climate := self.get_climate_by_id(climate_id)) is not None]
        biome = self.get_biome_by_id(biome_id)
        climates = self.list_climates()
        if biome is None:
            return climates
        filtered = [climate for climate in climates if biome.allows_climate(climate.climateId)]
        return filtered or climates
