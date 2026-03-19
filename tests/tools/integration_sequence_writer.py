import argparse
import json
from pathlib import Path

import main as game
from tests.tools.integration_test_orchestrator import build_menu_index
from src.domain.player_functions import Player
from src.services.menu_runtime import OriginalMessage


def _path_from_start(start_menu, target_menu):
    if start_menu.uniqueName == target_menu.uniqueName:
        return []

    reverse_path = []
    current = target_menu
    while current is not None and current.uniqueName != start_menu.uniqueName:
        reverse_path.append(current)
        current = current.parent

    if current is None:
        raise ValueError(f"Menu '{target_menu.uniqueName}' is not reachable from '{start_menu.uniqueName}'.")

    reverse_path.reverse()
    return reverse_path


def generate_sequence(menu_names: list[str], start_menu_name: str = "mainMenu"):
    game.initialize_game()
    menu_index = build_menu_index()
    if start_menu_name not in menu_index:
        raise ValueError(f"Start menu '{start_menu_name}' does not exist.")

    start_menu = menu_index[start_menu_name]
    if game.context.player_cache:
        sample_player = next(iter(game.context.player_cache.values()))
    else:
        # Integration sequence generation only needs placeholder replacement context.
        sample_player = Player(0)
        sample_player.playerName = "IntegrationTester"

    original_message = OriginalMessage(sample_player)
    actions = [{"type": "open", "menu": start_menu_name}]

    for menu_name in menu_names:
        if menu_name not in menu_index:
            raise ValueError(f"Requested menu '{menu_name}' does not exist.")
        target_menu = menu_index[menu_name]
        path = _path_from_start(start_menu, target_menu)

        for step in path:
            actions.append({"type": "select", "target": step.uniqueName})

        game.menu_service.update_menu_values(original_message, target_menu)
        visible_children = game.menu_service.get_visible_child_menus(target_menu, original_message)
        for child, _label in visible_children:
            actions.append({"type": "select", "target": child.uniqueName})
            actions.append({"type": "back"})

        for _ in path:
            actions.append({"type": "back"})

    return {
        "start_menu": start_menu_name,
        "actions": actions,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate an integration test sequence that presses all child buttons for given menus."
    )
    parser.add_argument("--menus", nargs="+", required=True, help="List of menu uniqueName values to test.")
    parser.add_argument("--start-menu", default="mainMenu", help="Starting menu uniqueName. Default: mainMenu")
    parser.add_argument("--output", required=True, help="Output JSON file path.")
    args = parser.parse_args()

    sequence = generate_sequence(args.menus, args.start_menu)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sequence, f, indent=4, ensure_ascii=False)

    print(f"Wrote integration sequence to {output_path}")


if __name__ == "__main__":
    main()


