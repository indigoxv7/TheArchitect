from __future__ import annotations

from src.services.mission_map.generator import MissionMap, MissionMapNode, MissionMapSettings


def mission_map_settings_to_dict(settings: MissionMapSettings) -> dict:
    return {
        "total_nodes": int(settings.total_nodes),
        "narrowness": float(settings.narrowness),
        "connectedness": float(settings.connectedness),
        "dead_end_likelihood": float(settings.dead_end_likelihood),
        "seed": settings.seed,
        "row_step_limit": int(settings.row_step_limit),
        "forward_bias": float(settings.forward_bias),
        "forbid_edge_crossings": bool(settings.forbid_edge_crossings),
        "max_extra_edges_degree_cap": int(settings.max_extra_edges_degree_cap),
        "allow_skip_edges": bool(settings.allow_skip_edges),
        "max_column_step": int(settings.max_column_step),
        "node_separation": float(settings.node_separation),
        "node_jitter_fraction": float(settings.node_jitter_fraction),
    }


def mission_map_settings_from_dict(data: dict) -> MissionMapSettings:
    return MissionMapSettings(
        total_nodes=int(data.get("total_nodes", 1) or 1),
        narrowness=float(data.get("narrowness", 0.5) or 0.5),
        connectedness=float(data.get("connectedness", 0.25) or 0.25),
        dead_end_likelihood=float(data.get("dead_end_likelihood", 0.5) or 0.5),
        seed=(int(data.get("seed")) if data.get("seed", None) not in (None, "") else None),
        row_step_limit=int(data.get("row_step_limit", 2) or 2),
        forward_bias=float(data.get("forward_bias", 0.7) or 0.7),
        forbid_edge_crossings=bool(data.get("forbid_edge_crossings", True)),
        max_extra_edges_degree_cap=int(data.get("max_extra_edges_degree_cap", 4) or 4),
        allow_skip_edges=bool(data.get("allow_skip_edges", False)),
        max_column_step=int(data.get("max_column_step", 1) or 1),
        node_separation=float(data.get("node_separation", 1.0) or 1.0),
        node_jitter_fraction=float(data.get("node_jitter_fraction", 0.45) or 0.45),
    )


def mission_map_to_dict(mission_map: MissionMap) -> dict:
    return {
        "settings": mission_map_settings_to_dict(mission_map.settings),
        "column_count": int(mission_map.column_count),
        "row_count": int(mission_map.row_count),
        "start_node_id": int(mission_map.start_node_id),
        "nodes_by_id": {
            str(node_id): {
                "node_id": int(node.node_id),
                "column": int(node.column),
                "row": int(node.row),
                "x_position": float(node.x_position),
                "y_position": float(node.y_position),
            }
            for node_id, node in mission_map.nodes_by_id.items()
        },
        "adjacency_by_node": {
            str(node_id): [int(neighbor_id) for neighbor_id in sorted(neighbor_ids)]
            for node_id, neighbor_ids in mission_map.adjacency_by_node.items()
        },
        "node_ids_by_column": [[int(node_id) for node_id in column] for column in mission_map.node_ids_by_column],
    }


def mission_map_from_dict(data: dict) -> MissionMap:
    settings = mission_map_settings_from_dict(dict(data.get("settings", {}) or {}))
    nodes_by_id = {}
    for key, raw_node in dict(data.get("nodes_by_id", {}) or {}).items():
        node_id = int(raw_node.get("node_id", key) or key)
        nodes_by_id[node_id] = MissionMapNode(
            node_id=node_id,
            column=int(raw_node.get("column", 0) or 0),
            row=int(raw_node.get("row", 0) or 0),
            x_position=float(raw_node.get("x_position", 0.0) or 0.0),
            y_position=float(raw_node.get("y_position", 0.0) or 0.0),
        )
    adjacency_by_node = {
        int(node_id): {int(neighbor_id) for neighbor_id in neighbors}
        for node_id, neighbors in dict(data.get("adjacency_by_node", {}) or {}).items()
    }
    return MissionMap(
        settings=settings,
        column_count=int(data.get("column_count", 0) or 0),
        row_count=int(data.get("row_count", 0) or 0),
        start_node_id=int(data.get("start_node_id", 0) or 0),
        nodes_by_id=nodes_by_id,
        adjacency_by_node=adjacency_by_node,
        node_ids_by_column=[[int(node_id) for node_id in column] for column in data.get("node_ids_by_column", []) or []],
    )
