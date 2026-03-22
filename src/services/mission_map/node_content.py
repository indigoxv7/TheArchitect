from __future__ import annotations

from collections import Counter
from copy import deepcopy
import random
import re
from typing import Any

from src.domain.location_content import (
    DescriptionPack,
    FeatureTemplate,
    GeneratedFeatureState,
    GeneratedHookState,
    GeneratedNodeContent,
    HookTemplate,
    NodeGenerationProfile,
    NodeRoleTemplate,
    SceneDescriptionMode,
    SettingContext,
    normalize_tag_list,
)
from src.services.mission_map.overlay import MissionMapOverlay


TOKEN_PATTERN = re.compile(r"#([A-Za-z0-9_]+)#")


def _weighted_choice(items: list[Any], weight_func, rng: random.Random):
    if not items:
        return None
    weights = [max(0.0, float(weight_func(item) or 0.0)) for item in items]
    total = sum(weights)
    if total <= 0.0:
        return rng.choice(items)
    threshold = rng.random() * total
    running = 0.0
    for item, weight in zip(items, weights):
        running += weight
        if running >= threshold:
            return item
    return items[-1]


def sample_setting_context(environment_service, mission, seed: int | None = None, rng: random.Random | None = None) -> SettingContext:
    rng = rng or random.Random(seed)
    biome = environment_service.get_biome_by_id(getattr(mission, "biomeId", "")) or next(iter(environment_service.list_biomes()), None)
    if biome is None:
        raise ValueError("At least one biome must exist before generating node content.")
    terrain_candidates = environment_service.terrain_candidates_for_biome(biome.biomeId, getattr(mission, "terrainPoolIds", []))
    climate_candidates = environment_service.climate_candidates_for_biome(biome.biomeId, getattr(mission, "climatePoolIds", []))
    terrain = rng.choice(terrain_candidates) if terrain_candidates else None
    climate = rng.choice(climate_candidates) if climate_candidates else None
    if terrain is None or climate is None:
        raise ValueError("Node content generation requires at least one compatible terrain and climate.")
    profile = environment_service.get_generation_profile_by_id(getattr(mission, "nodeGenerationProfileId", "")) or environment_service.get_default_generation_profile()
    pack = environment_service.get_description_pack_by_id(getattr(mission, "descriptionPackId", "")) or environment_service.get_default_description_pack()
    return SettingContext(
        biomeId=biome.biomeId,
        biomeName=biome.name,
        terrainId=terrain.terrainId,
        terrainName=terrain.name,
        climateId=climate.climateId,
        climateName=climate.name,
        generationProfileId=getattr(profile, "generationProfileId", ""),
        descriptionPackId=getattr(pack, "descriptionPackId", ""),
        settingContextTags=normalize_tag_list(list(getattr(biome, "allTags", [])) + list(getattr(terrain, "allTags", [])) + list(getattr(climate, "allTags", []))),
        civilizationTags=list(getattr(biome, "civilizationPriors", [])),
        threatTags=list(getattr(biome, "threatPriors", [])),
        resourceTags=list(getattr(biome, "resourcePriors", [])),
        mythicTags=list(getattr(biome, "mythicPriors", [])),
        ecologyTags=list(getattr(biome, "ecologyPriors", [])),
    )


def _template_is_allowed(required_tags: list[str], excluded_tags: list[str], available_tags: list[str]) -> bool:
    available = set(normalize_tag_list(available_tags))
    if any(tag not in available for tag in normalize_tag_list(required_tags)):
        return False
    if any(tag in available for tag in normalize_tag_list(excluded_tags)):
        return False
    return True


def _anti_repetition_multiplier(counter: Counter, key: str, strength: float) -> float:
    repeats = max(0, int(counter.get(key, 0)))
    return max(0.15, 1.0 - (min(1.0, strength) * min(0.8, repeats * 0.18)))


def _feature_state_from_template(template: FeatureTemplate) -> GeneratedFeatureState:
    return GeneratedFeatureState(
        featureId=template.featureId,
        name=template.name,
        category=template.category,
        tags=list(template.tags),
        affordanceTags=list(template.affordanceTags),
        hazardTags=list(template.hazardTags),
        memoryTags=list(template.memoryTags or template.tags),
        visibleTags=list(template.visibleTags),
        metrics=dict(template.metrics),
        payload=deepcopy(template.payload),
        descriptionHints=list(template.localDescriptionHints),
    )


def _hook_state_from_template(template: HookTemplate) -> GeneratedHookState:
    return GeneratedHookState(
        hookId=template.hookId,
        name=template.name,
        hookType=template.hookType.name,
        tags=list(template.tags),
        memoryTags=list(template.memoryTags or template.tags),
        visibleText=template.visibleText,
        payload=deepcopy(template.payload),
    )


def _choose_role(environment_service, setting_context: SettingContext, profile: NodeGenerationProfile, rng: random.Random, role_counter: Counter) -> NodeRoleTemplate:
    roles = [role for role in environment_service.list_node_roles() if _template_is_allowed(role.requiredTags, role.excludedTags, setting_context.allTags)]
    if not roles:
        fallback = environment_service.list_node_roles()
        if not fallback:
            raise ValueError("At least one node role is required.")
        return fallback[0]
    return _weighted_choice(
        roles,
        lambda role: max(0.01, float(getattr(role, "weight", 1.0) or 1.0))
        * float(profile.roleWeights.get(role.roleId, 1.0) or 1.0)
        * _anti_repetition_multiplier(role_counter, role.roleId, profile.antiRepetitionStrength),
        rng,
    )


def _choose_features(environment_service, role: NodeRoleTemplate, setting_context: SettingContext, profile: NodeGenerationProfile, rng: random.Random, feature_counter: Counter) -> list[GeneratedFeatureState]:
    target_count = rng.randint(max(0, role.minFeatures or profile.minFeatures), max(role.minFeatures or profile.minFeatures, role.maxFeatures or profile.maxFeatures))
    available_tags = normalize_tag_list(setting_context.allTags + list(role.roleTags))
    features: list[GeneratedFeatureState] = []
    selected_ids: set[str] = set()
    attempts = 0
    while len(features) < target_count and attempts < 20:
        attempts += 1
        candidates = []
        for feature in environment_service.list_feature_templates():
            if feature.featureId in selected_ids:
                continue
            if not _template_is_allowed(feature.requiredTags, feature.excludedTags, available_tags):
                continue
            candidates.append(feature)
        if not candidates:
            break
        chosen = _weighted_choice(
            candidates,
            lambda feature: max(0.01, float(feature.weight or 0.0)) * _anti_repetition_multiplier(feature_counter, feature.featureId, profile.antiRepetitionStrength),
            rng,
        )
        if chosen is None:
            break
        state = _feature_state_from_template(chosen)
        features.append(state)
        selected_ids.add(chosen.featureId)
        available_tags = normalize_tag_list(available_tags + state.tags + state.affordanceTags + state.hazardTags)
    return features


def _choose_hooks(environment_service, role: NodeRoleTemplate, setting_context: SettingContext, features: list[GeneratedFeatureState], profile: NodeGenerationProfile, rng: random.Random, hook_counter: Counter) -> list[GeneratedHookState]:
    current_tags = normalize_tag_list(setting_context.allTags + list(role.roleTags) + [tag for feature in features for tag in (feature.tags + feature.affordanceTags + feature.hazardTags)])
    max_hooks = max(profile.minHooks, profile.maxHooks)
    if max_hooks <= 0:
        return []
    target_count = rng.randint(profile.minHooks, max_hooks)
    hooks: list[GeneratedHookState] = []
    selected_ids: set[str] = set()
    for _ in range(target_count):
        candidates = []
        for hook in environment_service.list_hook_templates():
            if hook.hookId in selected_ids:
                continue
            if not _template_is_allowed(hook.requiredTags, hook.excludedTags, current_tags):
                continue
            candidates.append(hook)
        if not candidates:
            break
        chosen = _weighted_choice(
            candidates,
            lambda hook: max(0.01, float(hook.weight or 0.0)) * (1.25 if hook.hookType.value in role.desiredHookTypes or hook.hookType.name in role.desiredHookTypes else 1.0) * _anti_repetition_multiplier(hook_counter, hook.hookId, profile.antiRepetitionStrength),
            rng,
        )
        if chosen is None:
            break
        hooks.append(_hook_state_from_template(chosen))
        selected_ids.add(chosen.hookId)
    return hooks


def _eligible_fragments(fragments, tags: list[str]) -> list:
    return [fragment for fragment in fragments if _template_is_allowed(fragment.requiredTags, fragment.excludedTags, tags)]


def _render_tokens(template: str, values: dict[str, str]) -> str:
    def _replace(match):
        return str(values.get(match.group(1), ""))
    return TOKEN_PATTERN.sub(_replace, template).replace("  ", " ").strip()


def render_local_node_description(setting_context: SettingContext, node_content: GeneratedNodeContent, description_pack: DescriptionPack, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    tags = list(node_content.canonicalTags)
    landmark = next((feature.name.lower() for feature in node_content.featureStates if feature.visibleTags), "the node itself")
    feature_names = [feature.name.lower() for feature in node_content.featureStates[:3]] or [node_content.roleName.lower()]
    tokens = {
        "biome": setting_context.biomeName.lower(),
        "terrain": setting_context.terrainName.lower(),
        "climate": setting_context.climateName.lower(),
        "role": node_content.roleName.lower(),
        "role_mood": node_content.roleName.lower(),
        "landmark": landmark,
        "feature_list": ", ".join(feature_names),
        "hazard": ", ".join(node_content.hazardTags[:2]) or "uncertain footing",
        "affordance": ", ".join(node_content.affordanceTags[:2]) or "get your bearings",
    }
    fragments = []
    for pool in (
        description_pack.openingFragments,
        description_pack.landmarkFragments,
        description_pack.atmosphereFragments,
        description_pack.hazardFragments if node_content.hazardTags else [],
        description_pack.affordanceFragments if node_content.affordanceTags else [],
        description_pack.closingFragments,
    ):
        eligible = _eligible_fragments(pool, tags)
        if not eligible:
            continue
        chosen = _weighted_choice(eligible, lambda fragment: max(0.01, float(fragment.weight or 0.0)), rng)
        if chosen is None:
            continue
        rendered = _render_tokens(chosen.text, tokens)
        if rendered:
            fragments.append(rendered)
    return " ".join(fragments).strip()


def _build_visible_summary(role: NodeRoleTemplate, features: list[GeneratedFeatureState], hooks: list[GeneratedHookState], node_content: GeneratedNodeContent) -> list[str]:
    lines = [f"Role: {role.name}"]
    if features:
        lines.append("Features: " + ", ".join(feature.name for feature in features[:4]))
    if node_content.hazardTags:
        lines.append("Hazards: " + ", ".join(node_content.hazardTags[:3]))
    if node_content.affordanceTags:
        lines.append("Affordances: " + ", ".join(node_content.affordanceTags[:3]))
    for hook in hooks[:2]:
        if hook.visibleText:
            lines.append(hook.visibleText)
    return lines


def generate_node_content_preview(environment_service, mission_map, mission, seed: int | None = None) -> tuple[SettingContext, dict[int, GeneratedNodeContent]]:
    rng = random.Random(seed if seed is not None else getattr(getattr(mission_map, "settings", None), "seed", None))
    setting_context = sample_setting_context(environment_service, mission, rng=rng)
    profile = environment_service.get_generation_profile_by_id(setting_context.generationProfileId) or environment_service.get_default_generation_profile()
    description_pack = environment_service.get_description_pack_by_id(setting_context.descriptionPackId) or environment_service.get_default_description_pack()
    if profile is None or description_pack is None:
        raise ValueError("Node generation requires at least one description pack and generation profile.")

    role_counter: Counter = Counter()
    feature_counter: Counter = Counter()
    hook_counter: Counter = Counter()
    node_contents: dict[int, GeneratedNodeContent] = {}

    for node_id in sorted(mission_map.nodes_by_id.keys()):
        role = _choose_role(environment_service, setting_context, profile, rng, role_counter)
        role_counter[role.roleId] += 1
        features = _choose_features(environment_service, role, setting_context, profile, rng, feature_counter)
        for feature in features:
            feature_counter[feature.featureId] += 1
        hooks = _choose_hooks(environment_service, role, setting_context, features, profile, rng, hook_counter)
        for hook in hooks:
            hook_counter[hook.hookId] += 1

        feature_tags = [tag for feature in features for tag in feature.tags]
        affordance_tags = list(role.desiredAffordanceTags) + [tag for feature in features for tag in feature.affordanceTags]
        hazard_tags = list(role.desiredHazardTags) + [tag for feature in features for tag in feature.hazardTags]
        hook_tags = [tag for hook in hooks for tag in hook.tags]
        memory_tags = [tag for feature in features for tag in feature.memoryTags] + [tag for hook in hooks for tag in hook.memoryTags]
        canonical_tags = normalize_tag_list(setting_context.allTags + list(role.roleTags) + feature_tags + affordance_tags + hazard_tags + hook_tags + memory_tags)
        node_content = GeneratedNodeContent(
            nodeId=int(node_id),
            sceneDisplayName=f"{setting_context.terrainName} | {role.name}",
            battleTerrainLabel=f"{setting_context.terrainName} | {role.name}",
            roleId=role.roleId,
            roleName=role.name,
            roleTags=list(role.roleTags),
            settingContextTags=list(setting_context.allTags),
            featureTags=feature_tags,
            affordanceTags=affordance_tags,
            hazardTags=hazard_tags,
            hookTags=hook_tags,
            memoryTags=memory_tags,
            canonicalTags=canonical_tags,
            featureStates=features,
            hookStates=hooks,
        )
        node_content.visibleSummaryLines = _build_visible_summary(role, features, hooks, node_content)
        node_content.localDescription = render_local_node_description(setting_context, node_content, description_pack, rng=rng)
        node_contents[int(node_id)] = node_content
    return setting_context, node_contents


TREASURE_ICON_TAG = "treasure"
CLUE_ICON_TAG = "clue"
HOSTILE_ICON_TAG = "hostile_presence"


def apply_overlay_to_node_contents(node_contents: dict[int, GeneratedNodeContent], overlay: MissionMapOverlay) -> dict[int, GeneratedNodeContent]:
    for node_id, node_content in node_contents.items():
        if int(overlay.nanoByNode.get(node_id, 0) or 0) > 0:
            node_content.hookStates.append(
                GeneratedHookState(
                    hookId=f"generated_treasure_{node_id}",
                    name="Nano Cache",
                    hookType="TREASURE",
                    tags=[TREASURE_ICON_TAG],
                    memoryTags=[TREASURE_ICON_TAG],
                    visibleText="There are signs of hidden valuables here.",
                    payload={"kind": "treasure", "nano_amount": int(overlay.nanoByNode[node_id])},
                )
            )
            node_content.hookTags = normalize_tag_list(node_content.hookTags + [TREASURE_ICON_TAG])
        if node_id in overlay.clueTargetNodeByNode:
            node_content.hookStates.append(
                GeneratedHookState(
                    hookId=f"generated_clue_{node_id}",
                    name="Tracking Clue",
                    hookType="CLUE",
                    tags=[CLUE_ICON_TAG],
                    memoryTags=[CLUE_ICON_TAG],
                    visibleText="A clue here could point toward another occupied node.",
                    payload={"kind": "clue", "target_node_id": int(overlay.clueTargetNodeByNode[node_id])},
                )
            )
            node_content.hookTags = normalize_tag_list(node_content.hookTags + [CLUE_ICON_TAG])
        if overlay.unitsByNode.get(node_id):
            node_content.hookTags = normalize_tag_list(node_content.hookTags + [HOSTILE_ICON_TAG])
        node_content.canonicalTags = normalize_tag_list(node_content.canonicalTags + node_content.hookTags)
        node_content.memoryTags = normalize_tag_list(node_content.memoryTags + node_content.hookTags)
    return node_contents


def build_scene_description_prompt_packet(setting_context: SettingContext, node_content: GeneratedNodeContent) -> dict[str, Any]:
    return {
        "setting_context": setting_context.to_dict(),
        "node": node_content.to_dict(),
        "instructions": {
            "max_sentences": 4,
            "focus": "arrival_description",
        },
    }
