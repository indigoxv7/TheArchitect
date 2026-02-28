import argparse
import asyncio
import json
from pathlib import Path

import main as game


def _walk_menu(menu, index: dict[str, object]):
    if menu.uniqueName in index:
        return
    index[menu.uniqueName] = menu
    for child in menu.Options:
        _walk_menu(child, index)


def build_menu_index() -> dict[str, object]:
    index: dict[str, object] = {}
    _walk_menu(game.rootMenu, index)
    _walk_menu(game.newPlayerMenu, index)
    return index


def _find_visible_child_menu(current_menu, original_message, target_name: str):
    for child_menu, _label in game.GetVisibleChildMenus(current_menu, original_message):
        if child_menu.uniqueName == target_name:
            return child_menu
    return None


async def run_sequence_file(sequence_file: str):
    game.Initialize()

    with open(sequence_file, "r", encoding="utf-8-sig") as f:
        sequence = json.load(f)

    user_id = int(sequence.get("user_id", 191980469670248448))
    display_name = sequence.get("display_name", "IntegrationTester")
    start_menu_name = sequence.get("start_menu", "mainMenu")
    actions = sequence.get("actions", [])

    interface = game.ConsoleMenuInterface(user_id=user_id, display_name=display_name)
    menu_index = build_menu_index()
    if start_menu_name not in menu_index:
        raise ValueError(f"Start menu '{start_menu_name}' does not exist.")

    current_menu = None
    original_message = None

    for i, action in enumerate(actions):
        print(f"[INPUT {i + 1}] {action}")
        action_type = action.get("type")

        if action_type == "open":
            menu_name = action.get("menu", start_menu_name)
            if menu_name not in menu_index:
                raise ValueError(f"Action open references unknown menu '{menu_name}'.")
            original_message, current_menu = await game.display_menu_with_interface(interface, menu_index[menu_name])
            continue

        if original_message is None or current_menu is None:
            raise ValueError("Sequence must call an open action before navigation actions.")

        if action_type == "select":
            target = action.get("target")
            target_menu = _find_visible_child_menu(current_menu, original_message, target)
            if target_menu is None:
                visible = [m.uniqueName for m, _ in game.GetVisibleChildMenus(current_menu, original_message)]
                raise ValueError(f"Menu '{target}' is not selectable from '{current_menu.uniqueName}'. Visible: {visible}")
            current_menu = await game.update_menu_with_interface(interface, target_menu, original_message)
            continue

        if action_type == "back":
            if current_menu.parent is None:
                raise ValueError(f"Cannot go back from root menu '{current_menu.uniqueName}'.")
            current_menu = await game.update_menu_with_interface(interface, current_menu.parent, original_message)
            continue

        if action_type == "assert_menu":
            expected_menu = action.get("target")
            if current_menu.uniqueName != expected_menu:
                raise AssertionError(f"Expected current menu '{expected_menu}', got '{current_menu.uniqueName}'.")
            continue

        raise ValueError(f"Unknown action type '{action_type}'.")

    print("[RESULT] Integration sequence completed.")


def main():
    parser = argparse.ArgumentParser(description="Run JSON-driven menu integration tests.")
    parser.add_argument("sequence_file", help="Path to integration sequence JSON file.")
    args = parser.parse_args()

    sequence_path = Path(args.sequence_file)
    if not sequence_path.exists():
        raise FileNotFoundError(f"Sequence file not found: {sequence_path}")

    asyncio.run(run_sequence_file(str(sequence_path)))


if __name__ == "__main__":
    main()
