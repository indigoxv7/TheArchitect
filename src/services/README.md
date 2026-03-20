# Services

## Purpose
`src/services` is the orchestration layer for gameplay systems, content loading, Discord interaction flow, OpenAI integration, combat, menu rendering, and admin-facing operations.

This directory should coordinate domain models and persistence stores rather than duplicating model state or embedding raw file/database logic.

## Entry points
- Main modules: service facades such as `player_service.py`, `menu_service.py`, `battle/`, `menu_runtime/`, `character_generation/`, `mission_map/`
- Called by: `main.py`, admin tools, tests, and integration flows

## Public interfaces
- `BattleService` - battle lifecycle orchestration
- `MenuRuntimeService` / `MenuService` - menu rendering, action dispatch, and menu loading
- Content services (`SpellService`, `ItemService`, `RaceService`, `MissionService`, `CampaignService`, `EnvironmentService`) - load and serve game data
- `PlayerService` / `MainCharacterMemoryService` / `OpenAINarrativeService` - player state, memory, and narrative integration

## Invariants and boundaries
- Keep persistent IO in `src/persistence`.
- Keep Discord interaction payload logic out of `src/domain`.
- Wire new services through `main.py` and the relevant tests rather than creating hidden globals.

## File map
| Path | Responsibility |
|------|----------------|
| `player_service.py` | Player loading, synchronization, and recovery behavior |
| `menu_service.py` | Menu loading and context/menu graph setup |
| `battle/` | Battle orchestration internals behind `BattleService` |
| `menu_runtime/` | Discord and console interaction runtime behind `MenuRuntimeService` |
| `character_generation/` | Main-character and race-based generation helpers |
| `mission_map/` | Mission-map generation and preview image helpers |
| `openai_narrative_service.py` | OpenAI-backed narrative and embedding client wrapper |

## Tests
```bash
python -m pytest -q tests/test_battle_service.py tests/test_menu_runtime.py tests/test_player_service.py tests/test_main_character_memory_service.py
```

## Common changes
- Add a new service: define one clear facade, wire it in `main.py`, and add focused tests at the service boundary.
- Refactor orchestration: keep business rules in domain/support modules and keep the public service contract stable.
- Debugging: start from the service test or `main.py` wiring path before opening downstream helpers.
