# Menu Runtime

## Purpose
`src/services/menu_runtime` owns live menu interaction flow for Discord and console contexts: rendering, navigation, action dispatch, draft editing, and modal handling.

Menu definitions stay in `GameData/Menus` and are loaded by `MenuService`; menu model classes stay in `src/ui/menu`.

## Entry points
- Main module(s): `__init__.py`, `service.py`, `interaction.py`
- Called by: `main.py` slash commands and menu-focused tests

## Public interfaces
- `MenuRuntimeService` - main facade for displaying and advancing menus
- `DiscordMenuInterface` / `ConsoleMenuInterface` - runtime adapters for output/input surfaces
- `MenuInterface` / `OriginalMessage` - shared interface contracts between runtime layers

## Invariants and boundaries
- Keep menu data loading in `MenuService`, not here.
- Keep menu models in `src/ui/menu`.
- Keep Discord-specific payload shaping in this package, not in domain models or persistence.

## File map
| Path | Responsibility |
|------|----------------|
| `service.py` | Facade and runtime coordination helpers |
| `interaction.py` | Display flow and interface-specific runtime behavior |
| `actions.py` | Special menu action dispatch and handlers |
| `modals.py` | Discord modal classes for menu editing flows |
| `parsers.py` / `drafts.py` | Draft parsing and menu-edit helper state |

## Tests
```bash
python -m pytest -q tests/test_menu_runtime.py tests/test_menu_view.py
```

## Common changes
- Add a menu action: register it in `actions.py` and cover it with a runtime test.
- Refactor interaction flow: keep the `MenuRuntimeService` facade stable for `main.py`.
- Debugging: start from `tests/test_menu_runtime.py` and only open Discord view code if the failure is rendering-specific.
