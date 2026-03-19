# Domain

## Purpose
`src/domain` owns the core gameplay models and value types used throughout the project: characters, players, races, units, missions, combat state, items, and related helpers.

It should stay focused on in-memory game state and serialization-friendly structures. Discord handlers, Tkinter widgets, and file/database access should stay outside this directory.

## Entry points
- Main modules: `character.py`, `main_character.py`, `player_functions.py`, `race.py`, `unit.py`, `items/`, `mission/`, `combat/`
- Called by: `src/services`, persistence stores, and admin editor flows

## Public interfaces
- `Character` / `MainCharacter` - main playable and NPC character models
- `Player` and save helpers in `player_functions.py` - player roster, progress, and save compatibility
- `Race` / `Unit` - reusable content models for race and unit definitions
- `MissionTemplate` and combat state packages - mission definitions and battle state payloads

## Invariants and boundaries
- Keep Discord-specific and Tkinter-specific behavior out of this directory.
- Prefer state models and conversion helpers over orchestration logic.
- Preserve save and catalog payload compatibility when changing `to_dict` / `from_dict` style helpers.

## File map
| Path | Responsibility |
|------|----------------|
| `character.py` | Core combatant model and derived stats |
| `main_character.py` | Main-character specific profile, hobby, and LLM-control state |
| `player_functions.py` | Player state, save/load compatibility, and legacy module alias handling |
| `items/` | Item, gear, weapon, armor, and consumable models |
| `mission/` | Mission template, objective, and statistics models |
| `combat/` | Encounter, unit-state, and battle-state models |

## Tests
```bash
python -m pytest -q tests/test_main_character.py tests/test_combat_timing.py tests/test_player_save.py
```

## Common changes
- Add model fields: update construction, serialization helpers, and the affected service tests together.
- Refactor models: keep save/catalog payload shapes stable unless the change explicitly includes a migration.
- Debugging: start from the service test that builds or loads the model before opening multiple domain files.
