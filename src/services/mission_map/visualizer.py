from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.services.mission_map.generator import MissionMap
from src.services.mission_map.overlay import MissionMapOverlay


def _node_positions(
    mission_map: MissionMap,
    width: int,
    height: int,
    margin: int,
) -> dict[int, tuple[float, float]]:
    usable_width = max(1, width - (margin * 2))
    usable_height = max(1, height - (margin * 2))

    x_values = [float(getattr(node, "x_position", node.column)) for node in mission_map.nodes_by_id.values()]
    y_values = [float(getattr(node, "y_position", node.row)) for node in mission_map.nodes_by_id.values()]
    min_x = min(x_values) if x_values else 0.0
    max_x = max(x_values) if x_values else 1.0
    min_y = min(y_values) if y_values else 0.0
    max_y = max(y_values) if y_values else 1.0
    x_span = max(1e-6, max_x - min_x)
    y_span = max(1e-6, max_y - min_y)

    positions: dict[int, tuple[float, float]] = {}
    for node_id, node in mission_map.nodes_by_id.items():
        x_value = float(getattr(node, "x_position", node.column))
        y_value = float(getattr(node, "y_position", node.row))
        x = margin + (((x_value - min_x) / x_span) * usable_width if x_span else usable_width / 2)
        y = margin + (((y_value - min_y) / y_span) * usable_height if y_span else usable_height / 2)
        positions[node_id] = (x, y)
    return positions


def _load_annotation_font(size: int) -> ImageFont.ImageFont:
    for font_name in ("seguiemj.ttf", "Segoe UI Emoji", "arial.ttf"):
        try:
            return ImageFont.truetype(font_name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _feature_annotation_text(
    overlay: MissionMapOverlay | None,
    node_id: int,
    visible_feature_node_ids: set[int] | None,
) -> str:
    if overlay is None:
        return ""
    if visible_feature_node_ids is not None and node_id not in visible_feature_node_ids:
        return ""
    parts: list[str] = []
    count = int(overlay.characterCountByNode.get(node_id, 0) or 0)
    if count > 0:
        parts.append(f"\U0001F464{count}")
    if int(overlay.nanoByNode.get(node_id, 0) or 0) > 0:
        parts.append("\U0001F4B0")
    if node_id in overlay.clueTargetNodeByNode:
        parts.append("\U0001F43E")
    return " ".join(parts)


def _rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    return tuple(int(value[index : index + 2], 16) for index in range(0, 6, 2)) + (max(0, min(255, alpha)),)


def render_mission_map_image(
    mission_map: MissionMap,
    width: int = 960,
    height: int = 540,
    margin: int = 48,
    overlay: MissionMapOverlay | None = None,
    visited_node_ids: set[int] | None = None,
    revealed_node_ids: set[int] | None = None,
    current_node_id: int | None = None,
    accessible_labels_by_node: dict[int, str] | None = None,
    visible_feature_node_ids: set[int] | None = None,
) -> Image.Image:
    image = Image.new("RGBA", (width, height), _rgba("#fbf7ef"))
    draw = ImageDraw.Draw(image)
    positions = _node_positions(mission_map, width=width, height=height, margin=margin)

    visited = {int(node_id) for node_id in (visited_node_ids or set())}
    revealed = {int(node_id) for node_id in (revealed_node_ids or set())}
    accessible = {int(node_id): str(label or "") for node_id, label in (accessible_labels_by_node or {}).items()}
    visible_nodes = set(visited) | set(revealed)
    if current_node_id is not None:
        visible_nodes.add(int(current_node_id))
    if visible_feature_node_ids is None:
        visible_feature_node_ids = set(mission_map.nodes_by_id.keys())

    for left_node_id, right_node_id in mission_map.edges():
        left = positions[left_node_id]
        right = positions[right_node_id]
        edge_visible = left_node_id in visible_nodes and right_node_id in visible_nodes
        color = _rgba("#6b7c85", 235 if edge_visible else 72)
        draw.line((left[0], left[1], right[0], right[1]), fill=color, width=3)

    node_radius = 11
    annotation_font = _load_annotation_font(18)
    letter_font = _load_annotation_font(16)
    for node_id, (x, y) in positions.items():
        annotation = _feature_annotation_text(overlay, node_id, visible_feature_node_ids)
        if annotation:
            bounds = draw.textbbox((0, 0), annotation, font=annotation_font)
            text_width = bounds[2] - bounds[0]
            text_height = bounds[3] - bounds[1]
            left = x - (text_width / 2) - 4
            top = y - node_radius - text_height - 10
            right = x + (text_width / 2) + 4
            bottom = top + text_height + 4
            draw.rounded_rectangle((left, top, right, bottom), radius=4, fill=_rgba("#fff7dd", 235), outline=_rgba("#9f8f68", 240))
            draw.text((x - (text_width / 2), top + 2), annotation, fill=_rgba("#3a2a14", 255), font=annotation_font)

        node_visible = node_id in visible_nodes
        alpha = 255 if node_visible else 80
        fill = _rgba("#24577a", alpha)
        outline = _rgba("#163449", min(255, alpha + 10))
        if node_id == mission_map.start_node_id:
            fill = _rgba("#2f7d32", alpha)
        if current_node_id is not None and node_id == int(current_node_id):
            fill = _rgba("#d68910", 255)
            outline = _rgba("#7d4c00", 255)
        elif node_id in accessible:
            fill = _rgba("#3572a5", max(alpha, 180))
            outline = _rgba("#163449", max(alpha, 200))

        draw.ellipse(
            (x - node_radius, y - node_radius, x + node_radius, y + node_radius),
            fill=fill,
            outline=outline,
            width=2,
        )

        if node_id in accessible and accessible[node_id]:
            label = accessible[node_id]
            bounds = draw.textbbox((0, 0), label, font=letter_font)
            text_width = bounds[2] - bounds[0]
            text_height = bounds[3] - bounds[1]
            draw.text(
                (x - (text_width / 2), y - (text_height / 2) - 1),
                label,
                fill=_rgba("#ffffff", 255),
                font=letter_font,
            )

    return image


def save_mission_map_image(
    mission_map: MissionMap,
    path: str | Path,
    width: int = 960,
    height: int = 540,
    margin: int = 48,
    overlay: MissionMapOverlay | None = None,
    visited_node_ids: set[int] | None = None,
    revealed_node_ids: set[int] | None = None,
    current_node_id: int | None = None,
    accessible_labels_by_node: dict[int, str] | None = None,
    visible_feature_node_ids: set[int] | None = None,
) -> Path:
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    image = render_mission_map_image(
        mission_map,
        width=width,
        height=height,
        margin=margin,
        overlay=overlay,
        visited_node_ids=visited_node_ids,
        revealed_node_ids=revealed_node_ids,
        current_node_id=current_node_id,
        accessible_labels_by_node=accessible_labels_by_node,
        visible_feature_node_ids=visible_feature_node_ids,
    )
    image.save(target_path, format="PNG")
    return target_path
