from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
import random

from src.domain.mission import MissionMapGenerationRange, MissionTemplate
from src.services.mission_map.generator import MissionMap, MissionMapSettings, generate_mission_map


START_NODE_CHARACTER_WEIGHT = 0.12


@dataclass
class MissionMapOverlay:
    unitsByNode: dict[int, list[object]] = field(default_factory=dict)
    nanoByNode: dict[int, int] = field(default_factory=dict)
    clueTargetNodeByNode: dict[int, int] = field(default_factory=dict)

    def clone(self) -> "MissionMapOverlay":
        return MissionMapOverlay(
            unitsByNode={node_id: list(units) for node_id, units in self.unitsByNode.items()},
            nanoByNode=dict(self.nanoByNode),
            clueTargetNodeByNode=dict(self.clueTargetNodeByNode),
        )

    @property
    def characterCountByNode(self) -> dict[int, int]:
        return {node_id: len(units) for node_id, units in self.unitsByNode.items() if units}

    @property
    def totalPlacedCharacters(self) -> int:
        return sum(len(units) for units in self.unitsByNode.values())

    @property
    def totalNano(self) -> int:
        return sum(max(0, int(amount or 0)) for amount in self.nanoByNode.values())


def build_map_settings_from_range(
    map_generation_range: MissionMapGenerationRange | dict | None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> MissionMapSettings:
    generation_range = (
        map_generation_range
        if isinstance(map_generation_range, MissionMapGenerationRange)
        else MissionMapGenerationRange.from_dict(map_generation_range)
    )
    sampled = generation_range.sample_values(rng=rng, seed=seed)
    return MissionMapSettings(**sampled)


def generate_map_from_range(
    map_generation_range: MissionMapGenerationRange | dict | None,
    seed: int | None = None,
) -> MissionMap:
    return generate_mission_map(build_map_settings_from_range(map_generation_range, seed=seed))


def place_characters_on_map(
    mission_map: MissionMap,
    mission: MissionTemplate,
    populated_preview,
    existing_overlay: MissionMapOverlay | None = None,
    seed: int | None = None,
) -> MissionMapOverlay:
    overlay = existing_overlay.clone() if existing_overlay is not None else MissionMapOverlay()
    overlay.unitsByNode = {}

    rng = random.Random(seed if seed is not None else mission_map.settings.seed)
    candidate_node_ids = sorted(mission_map.nodes_by_id.keys())
    if not candidate_node_ids or populated_preview is None:
        return overlay

    preview_by_allegiance = {result.allegianceId: list(result.generatedUnits) for result in populated_preview.allegiances}
    for config in mission.allegianceConfigs:
        units = list(preview_by_allegiance.get(config.allegianceId, []))
        if not units:
            continue
        rng.shuffle(units)
        _place_allegiance_units(mission_map, overlay.unitsByNode, candidate_node_ids, config, units, rng)

    overlay.clueTargetNodeByNode = {}
    return overlay


def generate_treasure_overlay(
    mission_map: MissionMap,
    existing_overlay: MissionMapOverlay | None = None,
    seed: int | None = None,
) -> MissionMapOverlay:
    overlay = existing_overlay.clone() if existing_overlay is not None else MissionMapOverlay()
    overlay.nanoByNode = {}

    candidate_node_ids = sorted(mission_map.nodes_by_id.keys())
    if not candidate_node_ids:
        return overlay

    rng = random.Random(seed if seed is not None else mission_map.settings.seed)
    max_nodes = max(1, min(len(candidate_node_ids), max(2, mission_map.node_count // 6)))
    min_nodes = max(1, min(max_nodes, max(1, mission_map.node_count // 12)))
    treasure_node_count = rng.randint(min_nodes, max_nodes)
    selected_node_ids = rng.sample(candidate_node_ids, k=min(treasure_node_count, len(candidate_node_ids)))
    for node_id in selected_node_ids:
        overlay.nanoByNode[node_id] = rng.randint(50, 250)
    return overlay


def generate_clue_overlay(
    mission_map: MissionMap,
    existing_overlay: MissionMapOverlay | None = None,
    seed: int | None = None,
) -> MissionMapOverlay:
    overlay = existing_overlay.clone() if existing_overlay is not None else MissionMapOverlay()
    overlay.clueTargetNodeByNode = {}
    character_node_ids = sorted(node_id for node_id, units in overlay.unitsByNode.items() if units)
    if not character_node_ids:
        raise ValueError('Generate character placements before generating clues.')

    rng = random.Random(seed if seed is not None else mission_map.settings.seed)
    candidate_node_ids = [
        node_id for node_id in sorted(mission_map.nodes_by_id.keys()) if node_id not in character_node_ids
    ]
    if not candidate_node_ids:
        candidate_node_ids = sorted(mission_map.nodes_by_id.keys())

    clue_count = min(len(candidate_node_ids), max(1, min(max(1, mission_map.node_count // 8), len(character_node_ids))))
    selected_clue_nodes = rng.sample(candidate_node_ids, k=clue_count)
    targeted_node_ids: set[int] = set()
    for clue_node_id in selected_clue_nodes:
        target_node_id = _nearest_character_node(
            mission_map,
            clue_node_id,
            character_node_ids,
            targeted_node_ids,
        )
        if target_node_id is None:
            continue
        overlay.clueTargetNodeByNode[clue_node_id] = target_node_id
        targeted_node_ids.add(target_node_id)
    return overlay


def generate_all_map_features(
    mission_map: MissionMap,
    mission: MissionTemplate,
    populated_preview,
    existing_overlay: MissionMapOverlay | None = None,
    seed: int | None = None,
) -> MissionMapOverlay:
    overlay = place_characters_on_map(
        mission_map,
        mission,
        populated_preview,
        existing_overlay=existing_overlay,
        seed=seed,
    )
    overlay = generate_treasure_overlay(mission_map, existing_overlay=overlay, seed=None if seed is None else seed + 1)
    overlay = generate_clue_overlay(mission_map, existing_overlay=overlay, seed=None if seed is None else seed + 2)
    return overlay


def _place_allegiance_units(mission_map, units_by_node, candidate_node_ids, config, units, rng):
    used_node_ids: list[int] = []
    effective_cluster_probability = max(
        0.0,
        min(
            1.0,
            float(getattr(config, 'clusterProbability', 0.0) or 0.0)
            + rng.uniform(
                -float(getattr(config, 'clusterProbabilityVariance', 0.0) or 0.0),
                float(getattr(config, 'clusterProbabilityVariance', 0.0) or 0.0),
            ),
        ),
    )

    for unit in units:
        place_on_existing = bool(used_node_ids) and rng.random() < effective_cluster_probability
        if place_on_existing:
            node_id = _weighted_choice(
                used_node_ids,
                [max(1.0, len(units_by_node.get(existing_node_id, []))) for existing_node_id in used_node_ids],
                rng,
            )
        else:
            unused_node_ids = [node_id for node_id in candidate_node_ids if node_id not in used_node_ids]
            node_pool = unused_node_ids or candidate_node_ids
            node_id = _weighted_choice(
                node_pool,
                [START_NODE_CHARACTER_WEIGHT if node_id == mission_map.start_node_id else 1.0 for node_id in node_pool],
                rng,
            )
            if node_id not in used_node_ids:
                used_node_ids.append(node_id)
        units_by_node.setdefault(node_id, []).append(unit)


def _weighted_choice(options: list[int], weights: list[float], rng: random.Random) -> int:
    if not options:
        raise ValueError('Cannot choose from an empty sequence.')
    if len(options) != len(weights):
        raise ValueError('Options and weights must be the same length.')
    total_weight = sum(max(0.0, float(weight or 0.0)) for weight in weights)
    if total_weight <= 0.0:
        return rng.choice(options)
    threshold = rng.random() * total_weight
    running_weight = 0.0
    for option, weight in zip(options, weights):
        running_weight += max(0.0, float(weight or 0.0))
        if running_weight >= threshold:
            return option
    return options[-1]


def _nearest_character_node(
    mission_map: MissionMap,
    start_node_id: int,
    candidate_character_node_ids: list[int],
    excluded_node_ids: set[int],
) -> int | None:
    distances = _shortest_path_distances(mission_map, start_node_id)
    preferred_candidates = [node_id for node_id in candidate_character_node_ids if node_id not in excluded_node_ids]
    search_candidates = preferred_candidates or list(candidate_character_node_ids)
    reachable_candidates = [node_id for node_id in search_candidates if node_id in distances and node_id != start_node_id]
    if not reachable_candidates:
        return None
    reachable_candidates.sort(key=lambda node_id: (distances[node_id], node_id))
    return reachable_candidates[0]


def _shortest_path_distances(mission_map: MissionMap, start_node_id: int) -> dict[int, int]:
    distances = {start_node_id: 0}
    queue = deque([start_node_id])
    while queue:
        node_id = queue.popleft()
        current_distance = distances[node_id]
        for neighbor_id in mission_map.neighbors(node_id):
            if neighbor_id in distances:
                continue
            distances[neighbor_id] = current_distance + 1
            queue.append(neighbor_id)
    return distances
