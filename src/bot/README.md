# Bot Views

## Purpose
`src/bot` contains Discord-specific view classes and UI helpers used to render interactive controls for menus and battles.

This package should stay thin and presentation-oriented. Gameplay rules, persistence, and state transitions belong in the service layer.

## Entry points
- Main module(s): `views/menu_view.py`, `views/combat_view.py`
- Called by: `src/services/menu_runtime/interaction.py` and `src/services/battle_runtime_service.py`

## Public interfaces
- `SimpleMenu` - Discord `View` for the slash-command menu system
- `MenuButton` / `BackButton` - menu navigation buttons
- `normalize_button_emoji` - shared guard for optional button emoji values
- `CombatView` - Discord `View` for active battle controls

## Invariants and boundaries
- Keep Discord widget composition here, not in `src/domain`.
- Let services decide behavior; views should delegate through callbacks and runtime methods.
- Avoid direct file IO or save mutation in this package.

## File map
| Path | Responsibility |
|------|----------------|
| `views/menu_view.py` | Menu buttons and Discord menu view construction |
| `views/combat_view.py` | Battle-tab buttons and consumable selection UI |
| `__init__.py` | Package marker |

## Tests
```bash
python -m pytest -q tests/test_menu_view.py tests/test_menu_runtime.py
```

## Common changes
- Add a Discord menu control: update `views/menu_view.py`, then verify the runtime still builds the expected buttons.
- Add a battle control: update `views/combat_view.py`, then check the battle runtime path that handles the callback.
- Debugging: start with the menu or battle runtime test before opening both view modules.
