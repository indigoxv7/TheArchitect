from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
import math
import random


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def aspect_ratio_from_narrowness(narrowness: float) -> float:
    """
    narrowness:
      0.0 -> aspect ratio 1.0 (square-ish)
      0.5 -> aspect ratio 2.0 (twice as wide as tall)
      1.0 -> infinite (single row)
    """
    narrowness = clamp(narrowness, 0.0, 1.0)
    if narrowness >= 1.0:
        return float("inf")
    return 1.0 / (1.0 - narrowness)


def pick_grid_dimensions(total_nodes: int, narrowness: float) -> tuple[int, int]:
    if total_nodes <= 0:
        raise ValueError("total_nodes must be positive.")

    narrowness = clamp(narrowness, 0.0, 1.0)
    if narrowness >= 1.0:
        return total_nodes, 1

    target_aspect_ratio = aspect_ratio_from_narrowness(narrowness)
    best_dimensions: tuple[int, int] | None = None
    best_cost: float | None = None

    max_rows_to_try = min(total_nodes, max(2, int(math.ceil(math.sqrt(total_nodes))) * 4))
    for row_count in range(1, max_rows_to_try + 1):
        column_count = int(math.ceil(total_nodes / row_count))
        if column_count < row_count:
            continue

        actual_aspect_ratio = column_count / row_count
        unused_cells = (column_count * row_count) - total_nodes

        aspect_cost = abs(math.log(actual_aspect_ratio / target_aspect_ratio))
        waste_cost = 0.15 * (unused_cells / total_nodes)
        total_cost = aspect_cost + waste_cost

        if best_cost is None or total_cost < best_cost:
            best_cost = total_cost
            best_dimensions = (column_count, row_count)

    if best_dimensions is None:
        return total_nodes, 1

    return best_dimensions


def choose_distinct_rows(row_count: int, total_rows: int, rng: random.Random) -> list[int]:
    if row_count <= 0 or row_count > total_rows:
        raise ValueError("row_count must be between 1 and total_rows.")

    if row_count == total_rows:
        return list(range(total_rows))

    if row_count == 1:
        return [rng.randrange(total_rows)]

    target_rows = [index * (total_rows - 1) / (row_count - 1) for index in range(row_count)]
    available_rows = set(range(total_rows))
    selected_rows: list[int] = []

    for target_row in target_rows:
        desired_row = int(round(target_row + rng.uniform(-0.25, 0.25)))
        desired_row = max(0, min(total_rows - 1, desired_row))
        chosen_row = min(
            available_rows,
            key=lambda row_index: (abs(row_index - desired_row), rng.random()),
        )
        selected_rows.append(chosen_row)
        available_rows.remove(chosen_row)

    return sorted(selected_rows)


def would_cross(existing_edges_in_step: list[tuple[int, int]], from_row: int, to_row: int) -> bool:
    for existing_from_row, existing_to_row in existing_edges_in_step:
        if (from_row - existing_from_row) * (to_row - existing_to_row) < 0:
            return True
    return False


def connected_components_for(adjacency_by_node: dict[int, set[int]]) -> list[set[int]]:
    unvisited_node_ids = set(adjacency_by_node.keys())
    components: list[set[int]] = []

    while unvisited_node_ids:
        start_node_id = next(iter(unvisited_node_ids))
        stack = [start_node_id]
        visited_in_component: set[int] = set()

        while stack:
            current_node_id = stack.pop()
            if current_node_id in visited_in_component:
                continue

            visited_in_component.add(current_node_id)
            stack.extend(adjacency_by_node[current_node_id] - visited_in_component)

        unvisited_node_ids -= visited_in_component
        components.append(visited_in_component)

    return components


@dataclass
class MissionMapNode:
    node_id: int
    column: int
    row: int


@dataclass
class MissionMapSettings:
    total_nodes: int
    narrowness: float
    connectedness: float
    dead_end_likelihood: float
    seed: int | None = None

    row_step_limit: int = 2
    forward_bias: float = 0.7
    forbid_edge_crossings: bool = True
    max_extra_edges_degree_cap: int = 4
    allow_skip_edges: bool = False
    max_column_step: int = 1

    def __post_init__(self) -> None:
        if self.total_nodes <= 0:
            raise ValueError("total_nodes must be positive.")
        if not (0.0 <= self.narrowness <= 1.0):
            raise ValueError("narrowness must be in [0, 1].")
        if not (0.0 <= self.connectedness <= 1.0):
            raise ValueError("connectedness must be in [0, 1].")
        if not (0.0 <= self.dead_end_likelihood <= 1.0):
            raise ValueError("dead_end_likelihood must be in [0, 1].")
        if self.row_step_limit < 0:
            raise ValueError("row_step_limit must be >= 0.")
        if not (0.0 <= self.forward_bias <= 1.0):
            raise ValueError("forward_bias must be in [0, 1].")
        if self.max_extra_edges_degree_cap < 2:
            raise ValueError("max_extra_edges_degree_cap should be >= 2.")
        if self.allow_skip_edges and self.max_column_step < 2:
            raise ValueError("max_column_step must be >= 2 when allow_skip_edges is enabled.")


@dataclass
class MissionMap:
    settings: MissionMapSettings
    column_count: int
    row_count: int
    start_node_id: int
    nodes_by_id: dict[int, MissionMapNode] = field(default_factory=dict)
    adjacency_by_node: dict[int, set[int]] = field(default_factory=dict)
    node_ids_by_column: list[list[int]] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes_by_id)

    @property
    def edge_count(self) -> int:
        return sum(len(neighbor_ids) for neighbor_ids in self.adjacency_by_node.values()) // 2

    def connect(self, node_a_id: int, node_b_id: int) -> None:
        if node_a_id == node_b_id:
            return

        self.adjacency_by_node[node_a_id].add(node_b_id)
        self.adjacency_by_node[node_b_id].add(node_a_id)

    def has_connection(self, node_a_id: int, node_b_id: int) -> bool:
        return node_b_id in self.adjacency_by_node[node_a_id]

    def degree(self, node_id: int) -> int:
        return len(self.adjacency_by_node[node_id])

    def neighbors(self, node_id: int) -> tuple[int, ...]:
        return tuple(
            sorted(
                self.adjacency_by_node[node_id],
                key=lambda neighbor_id: (
                    self.nodes_by_id[neighbor_id].column,
                    self.nodes_by_id[neighbor_id].row,
                    neighbor_id,
                ),
            )
        )

    def edges(self) -> tuple[tuple[int, int], ...]:
        edge_pairs: list[tuple[int, int]] = []
        for left_node_id, neighbor_ids in self.adjacency_by_node.items():
            for right_node_id in neighbor_ids:
                if left_node_id < right_node_id:
                    edge_pairs.append((left_node_id, right_node_id))

        edge_pairs.sort()
        return tuple(edge_pairs)


class MissionMapGenerator:
    def __init__(self, settings: MissionMapSettings):
        actual_seed = settings.seed
        if actual_seed is None:
            actual_seed = random.SystemRandom().randrange(0, 2**32)
        self.settings = replace(settings, seed=actual_seed)
        self.rng = random.Random(actual_seed)

    def generate(self) -> MissionMap:
        column_count, row_count = pick_grid_dimensions(
            self.settings.total_nodes,
            self.settings.narrowness,
        )

        node_counts_by_column = [self.settings.total_nodes // column_count] * column_count
        for column_index in range(self.settings.total_nodes % column_count):
            node_counts_by_column[column_index] += 1

        while any(node_count > row_count for node_count in node_counts_by_column):
            column_count += 1
            row_count = max(row_count, int(math.ceil(self.settings.total_nodes / column_count)))
            node_counts_by_column = [self.settings.total_nodes // column_count] * column_count
            for column_index in range(self.settings.total_nodes % column_count):
                node_counts_by_column[column_index] += 1

        nodes_by_id: dict[int, MissionMapNode] = {}
        adjacency_by_node: dict[int, set[int]] = {}
        node_ids_by_column: list[list[int]] = [[] for _ in range(column_count)]

        next_node_id = 0
        for column_index, node_count in enumerate(node_counts_by_column):
            row_indices = choose_distinct_rows(node_count, row_count, self.rng)
            for row_index in row_indices:
                node = MissionMapNode(
                    node_id=next_node_id,
                    column=column_index,
                    row=row_index,
                )
                nodes_by_id[node.node_id] = node
                adjacency_by_node[node.node_id] = set()
                node_ids_by_column[column_index].append(node.node_id)
                next_node_id += 1

            node_ids_by_column[column_index].sort(key=lambda node_id: nodes_by_id[node_id].row)

        start_node_id = self._choose_start_node(nodes_by_id, node_ids_by_column, row_count)

        mission_map = MissionMap(
            settings=replace(self.settings),
            column_count=column_count,
            row_count=row_count,
            start_node_id=start_node_id,
            nodes_by_id=nodes_by_id,
            adjacency_by_node=adjacency_by_node,
            node_ids_by_column=node_ids_by_column,
        )

        if self.settings.total_nodes == 1:
            return mission_map

        candidate_neighbors_by_node = self._build_candidate_neighbors(
            nodes_by_id,
            node_ids_by_column,
        )
        self._repair_candidate_connectivity(nodes_by_id, candidate_neighbors_by_node)

        selection_newest_bias = clamp(1.0 - self.settings.dead_end_likelihood, 0.0, 1.0)

        visited_node_ids: set[int] = {start_node_id}
        active_node_ids: list[int] = [start_node_id]
        edges_by_step: list[list[tuple[int, int]]] = [[] for _ in range(max(0, column_count - 1))]

        while active_node_ids:
            active_index = self._pick_active_index(active_node_ids, selection_newest_bias)
            current_node_id = active_node_ids[active_index]

            neighbor_node_id = self._pick_unvisited_neighbor(
                current_node_id=current_node_id,
                visited_node_ids=visited_node_ids,
                candidate_neighbors_by_node=candidate_neighbors_by_node,
                nodes_by_id=nodes_by_id,
            )

            if neighbor_node_id is None:
                active_node_ids.pop(active_index)
                continue

            self._add_connection(
                mission_map=mission_map,
                node_a_id=current_node_id,
                node_b_id=neighbor_node_id,
                edges_by_step=edges_by_step,
            )
            visited_node_ids.add(neighbor_node_id)
            active_node_ids.append(neighbor_node_id)

        for node_id in set(nodes_by_id.keys()) - visited_node_ids:
            candidate_neighbor_ids = candidate_neighbors_by_node[node_id]
            if candidate_neighbor_ids:
                mission_map.connect(node_id, self.rng.choice(list(candidate_neighbor_ids)))

        self._add_extra_connections(
            mission_map=mission_map,
            nodes_by_id=nodes_by_id,
            node_ids_by_column=node_ids_by_column,
            edges_by_step=edges_by_step,
        )

        return mission_map

    def _choose_start_node(
        self,
        nodes_by_id: dict[int, MissionMapNode],
        node_ids_by_column: list[list[int]],
        row_count: int,
    ) -> int:
        center_row = (row_count - 1) / 2.0
        return min(
            node_ids_by_column[0],
            key=lambda node_id: abs(nodes_by_id[node_id].row - center_row),
        )

    def _pick_active_index(self, active_node_ids: list[int], selection_newest_bias: float) -> int:
        if self.rng.random() < selection_newest_bias:
            return len(active_node_ids) - 1
        return self.rng.randrange(len(active_node_ids))

    def _pick_unvisited_neighbor(
        self,
        current_node_id: int,
        visited_node_ids: set[int],
        candidate_neighbors_by_node: dict[int, set[int]],
        nodes_by_id: dict[int, MissionMapNode],
    ) -> int | None:
        unvisited_neighbor_ids = [
            neighbor_id
            for neighbor_id in candidate_neighbors_by_node[current_node_id]
            if neighbor_id not in visited_node_ids
        ]

        if not unvisited_neighbor_ids:
            return None

        current_column = nodes_by_id[current_node_id].column

        def edge_weight(neighbor_id: int) -> float:
            neighbor_column = nodes_by_id[neighbor_id].column
            column_delta = neighbor_column - current_column

            if column_delta > 0:
                direction_weight = 1.0 + (self.settings.forward_bias * 2.0)
            else:
                direction_weight = 1.0 + ((1.0 - self.settings.forward_bias) * 0.5)

            row_distance = abs(nodes_by_id[neighbor_id].row - nodes_by_id[current_node_id].row)
            distance_weight = 1.0 / (1.0 + row_distance)
            return direction_weight * distance_weight

        weights = [edge_weight(neighbor_id) for neighbor_id in unvisited_neighbor_ids]
        total_weight = sum(weights)

        if total_weight <= 0.0:
            return self.rng.choice(unvisited_neighbor_ids)

        threshold = self.rng.random() * total_weight
        running_weight = 0.0

        for neighbor_id, weight in zip(unvisited_neighbor_ids, weights):
            running_weight += weight
            if running_weight >= threshold:
                return neighbor_id

        return unvisited_neighbor_ids[-1]

    def _build_candidate_neighbors(
        self,
        nodes_by_id: dict[int, MissionMapNode],
        node_ids_by_column: list[list[int]],
    ) -> dict[int, set[int]]:
        candidate_neighbors_by_node: dict[int, set[int]] = {node_id: set() for node_id in nodes_by_id}

        max_column_step = self.settings.max_column_step if self.settings.allow_skip_edges else 1

        for left_column in range(len(node_ids_by_column)):
            for step in range(1, max_column_step + 1):
                right_column = left_column + step
                if right_column >= len(node_ids_by_column):
                    continue

                for left_node_id in node_ids_by_column[left_column]:
                    for right_node_id in node_ids_by_column[right_column]:
                        row_delta = abs(nodes_by_id[left_node_id].row - nodes_by_id[right_node_id].row)
                        if row_delta <= self.settings.row_step_limit:
                            candidate_neighbors_by_node[left_node_id].add(right_node_id)
                            candidate_neighbors_by_node[right_node_id].add(left_node_id)

        return candidate_neighbors_by_node

    def _repair_candidate_connectivity(
        self,
        nodes_by_id: dict[int, MissionMapNode],
        candidate_neighbors_by_node: dict[int, set[int]],
    ) -> None:
        components = connected_components_for(candidate_neighbors_by_node)
        if len(components) <= 1:
            return

        while len(components) > 1:
            components.sort(key=len)
            smaller_component = components[0]
            larger_component = components[-1]

            larger_component_by_column: dict[int, list[int]] = defaultdict(list)
            for node_id in larger_component:
                larger_component_by_column[nodes_by_id[node_id].column].append(node_id)

            best_pair: tuple[int, int] | None = None
            best_score: int | None = None

            for node_id in smaller_component:
                node = nodes_by_id[node_id]
                for neighbor_column in (node.column - 1, node.column + 1):
                    candidate_ids = larger_component_by_column.get(neighbor_column)
                    if not candidate_ids:
                        continue

                    candidate_id = min(
                        candidate_ids,
                        key=lambda other_id: abs(nodes_by_id[other_id].row - node.row),
                    )
                    score = abs(nodes_by_id[candidate_id].row - node.row)
                    if best_score is None or score < best_score:
                        best_score = score
                        best_pair = (node_id, candidate_id)

            if best_pair is None and self.settings.allow_skip_edges:
                for left_node_id in smaller_component:
                    left_node = nodes_by_id[left_node_id]
                    for right_node_id in larger_component:
                        right_node = nodes_by_id[right_node_id]
                        if left_node.column == right_node.column:
                            continue

                        score = (abs(left_node.column - right_node.column) * 10) + abs(left_node.row - right_node.row)
                        if best_score is None or score < best_score:
                            best_score = score
                            best_pair = (left_node_id, right_node_id)

            if best_pair is None:
                best_pair = (next(iter(smaller_component)), next(iter(larger_component)))

            left_node_id, right_node_id = best_pair
            candidate_neighbors_by_node[left_node_id].add(right_node_id)
            candidate_neighbors_by_node[right_node_id].add(left_node_id)
            components = connected_components_for(candidate_neighbors_by_node)

    def _add_connection(
        self,
        mission_map: MissionMap,
        node_a_id: int,
        node_b_id: int,
        edges_by_step: list[list[tuple[int, int]]],
    ) -> None:
        node_a = mission_map.nodes_by_id[node_a_id]
        node_b = mission_map.nodes_by_id[node_b_id]

        if node_a.column <= node_b.column:
            left_node = node_a
            right_node = node_b
        else:
            left_node = node_b
            right_node = node_a

        if left_node.column != right_node.column:
            step_index = left_node.column
            if self.settings.forbid_edge_crossings and step_index < len(edges_by_step):
                if would_cross(edges_by_step[step_index], left_node.row, right_node.row):
                    mission_map.connect(node_a_id, node_b_id)
                    return

                edges_by_step[step_index].append((left_node.row, right_node.row))

        mission_map.connect(node_a_id, node_b_id)

    def _add_extra_connections(
        self,
        mission_map: MissionMap,
        nodes_by_id: dict[int, MissionMapNode],
        node_ids_by_column: list[list[int]],
        edges_by_step: list[list[tuple[int, int]]],
    ) -> None:
        connectedness = clamp(self.settings.connectedness, 0.0, 1.0)
        if connectedness <= 0.0:
            return

        max_column_step = self.settings.max_column_step if self.settings.allow_skip_edges else 1
        candidate_edges: list[tuple[int, int, int]] = []

        for left_column in range(len(node_ids_by_column)):
            for step in range(1, max_column_step + 1):
                right_column = left_column + step
                if right_column >= len(node_ids_by_column):
                    continue

                for left_node_id in node_ids_by_column[left_column]:
                    for right_node_id in node_ids_by_column[right_column]:
                        if mission_map.has_connection(left_node_id, right_node_id):
                            continue

                        row_delta = abs(nodes_by_id[left_node_id].row - nodes_by_id[right_node_id].row)
                        if row_delta <= self.settings.row_step_limit:
                            candidate_edges.append((left_node_id, right_node_id, left_column))

        self.rng.shuffle(candidate_edges)

        minimum_edge_count = mission_map.node_count - 1
        maximum_edge_count = mission_map.edge_count + len(candidate_edges)
        target_edge_count = int(round(minimum_edge_count + connectedness * (maximum_edge_count - minimum_edge_count)))
        target_edge_count = max(
            mission_map.edge_count,
            min(target_edge_count, maximum_edge_count),
        )
        remaining_edges_to_add = target_edge_count - mission_map.edge_count

        if remaining_edges_to_add <= 0:
            return

        leaf_preference = 1.0 - self.settings.dead_end_likelihood

        def degree_is_available(node_id: int) -> bool:
            return mission_map.degree(node_id) < self.settings.max_extra_edges_degree_cap

        def is_leaf(node_id: int) -> bool:
            return mission_map.degree(node_id) <= 1

        leaf_edges: list[tuple[int, int, int]] = []
        non_leaf_edges: list[tuple[int, int, int]] = []

        for candidate_edge in candidate_edges:
            left_node_id, right_node_id, _ = candidate_edge
            if not (degree_is_available(left_node_id) and degree_is_available(right_node_id)):
                continue

            if is_leaf(left_node_id) or is_leaf(right_node_id):
                leaf_edges.append(candidate_edge)
            else:
                non_leaf_edges.append(candidate_edge)

        ordered_edges = leaf_edges + non_leaf_edges if leaf_preference >= 0.5 else non_leaf_edges + leaf_edges

        added_edge_count = 0
        for left_node_id, right_node_id, step_index in ordered_edges:
            if added_edge_count >= remaining_edges_to_add:
                break

            if mission_map.has_connection(left_node_id, right_node_id):
                continue
            if not (degree_is_available(left_node_id) and degree_is_available(right_node_id)):
                continue

            if self.settings.forbid_edge_crossings and step_index < len(edges_by_step):
                if would_cross(
                    edges_by_step[step_index],
                    nodes_by_id[left_node_id].row,
                    nodes_by_id[right_node_id].row,
                ):
                    continue

                edges_by_step[step_index].append((nodes_by_id[left_node_id].row, nodes_by_id[right_node_id].row))

            mission_map.connect(left_node_id, right_node_id)
            added_edge_count += 1


def generate_mission_map(settings: MissionMapSettings) -> MissionMap:
    return MissionMapGenerator(settings).generate()
