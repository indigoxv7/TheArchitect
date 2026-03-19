# Battle

## Purpose
`src/services/battle` owns the internal battle engine behind `BattleService`: roster setup, exchange flow, targeting, formation, consumable handling, mission tracking, and battle memory integration.

This package should keep battle orchestration cohesive while leaving battle state models in `src/domain/combat` and persistence in `src/persistence`.

## Entry points
- Main module(s): `__init__.py`, `service.py`
- Called by: `main.py`, `battle_runtime_service.py`, combat simulations, and battle-focused tests

## Public interfaces
- `BattleService` - external facade for starting, advancing, and persisting battles
- `battle_setup.py` - encounter/player roster assembly
- `exchange_flow.py` / `damage_resolution.py` - turn-by-turn combat resolution
- `mission_tracking.py` - mission outcome and objective tracking

## Invariants and boundaries
- Keep public callers talking to `BattleService`, not the internal helper modules.
- Use `src/domain/combat` for battle state payloads instead of ad hoc dictionaries.
- Keep file persistence in `ActiveBattleStore` and related persistence adapters.

## File map
| Path | Responsibility |
|------|----------------|
| `service.py` | Public `BattleService` facade and high-level orchestration |
| `battle_setup.py` | Convert players, units, and encounters into runtime battle entities |
| `exchange_flow.py` | Turn order and exchange sequencing |
| `damage_resolution.py` | Attack resolution and damage application |
| `mission_tracking.py` | Objective progress and result summaries |

## Tests
```bash
python -m pytest -q tests/test_battle_service.py tests/test_combat_simulator_service.py tests/test_power_rating_service.py
```

## Common changes
- Add battle behavior: start at `service.py`, then isolate the rule in the smallest helper module that owns it.
- Refactor internals: preserve the `BattleService` API and battle-state payload compatibility.
- Debugging: reproduce with `tests/test_battle_service.py` before stepping into helper modules.
