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
    column_span = max(1, mission_map.column_count - 1)
    row_span = max(1, mission_map.row_count - 1)

    positions: dict[int, tuple[float, float]] = {}
    for node_id, node in mission_map.nodes_by_id.items():
        x = margin + ((node.column / column_span) * usable_width if column_span else usable_width / 2)
        y = margin + ((node.row / row_span) * usable_height if row_span else usable_height / 2)
        positions[node_id] = (x, y)
    return positions


def _load_annotation_font(size: int) -> ImageFont.ImageFont:
    for font_name in ('seguiemj.ttf', 'Segoe UI Emoji', 'arial.ttf'):
        try:
            return ImageFont.truetype(font_name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _feature_annotation_text(overlay: MissionMapOverlay | None, node_id: int) -> str:
    if overlay is None:
        return ''
    parts: list[str] = []
    count = int(overlay.characterCountByNode.get(node_id, 0) or 0)
    if count > 0:
        parts.append(f'\U0001F464{count}')
    if int(overlay.nanoByNode.get(node_id, 0) or 0) > 0:
        parts.append('\U0001F4B0')
    if node_id in overlay.clueTargetNodeByNode:
        parts.append('\U0001F43E')
    return ' '.join(parts)


def render_mission_map_image(
    mission_map: MissionMap,
    width: int = 960,
    height: int = 540,
    margin: int = 48,
    overlay: MissionMapOverlay | None = None,
) -> Image.Image:
    image = Image.new('RGB', (width, height), '#fbf7ef')
    draw = ImageDraw.Draw(image)
    positions = _node_positions(mission_map, width=width, height=height, margin=margin)

    for left_node_id, right_node_id in mission_map.edges():
        left = positions[left_node_id]
        right = positions[right_node_id]
        draw.line((left[0], left[1], right[0], right[1]), fill='#6b7c85', width=3)

    node_radius = 9
    annotation_font = _load_annotation_font(18)
    for node_id, (x, y) in positions.items():
        annotation = _feature_annotation_text(overlay, node_id)
        if annotation:
            bounds = draw.textbbox((0, 0), annotation, font=annotation_font)
            text_width = bounds[2] - bounds[0]
            text_height = bounds[3] - bounds[1]
            left = x - (text_width / 2) - 4
            top = y - node_radius - text_height - 10
            right = x + (text_width / 2) + 4
            bottom = top + text_height + 4
            draw.rounded_rectangle((left, top, right, bottom), radius=4, fill='#fff7dd', outline='#9f8f68')
            draw.text((x - (text_width / 2), top + 2), annotation, fill='#3a2a14', font=annotation_font)

        fill = '#2f7d32' if node_id == mission_map.start_node_id else '#24577a'
        outline = '#163449'
        draw.ellipse(
            (x - node_radius, y - node_radius, x + node_radius, y + node_radius),
            fill=fill,
            outline=outline,
            width=2,
        )

    return image


def save_mission_map_image(
    mission_map: MissionMap,
    path: str | Path,
    width: int = 960,
    height: int = 540,
    margin: int = 48,
    overlay: MissionMapOverlay | None = None,
) -> Path:
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    image = render_mission_map_image(mission_map, width=width, height=height, margin=margin, overlay=overlay)
    image.save(target_path, format='PNG')
    return target_path


