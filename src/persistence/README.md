# Persistence

## Purpose
`src/persistence` owns file and sqlite persistence for catalogs, menus, battles, tuning data, and memory storage.

This directory should be the boundary for reading and writing repo data assets. Keep Discord handlers, Tkinter code, and high-level orchestration out of these modules.

## Entry points
- Main modules: the `*_store.py` files and `player_memory/`
- Called by: `src/services`, `main.py`, and persistence-focused tests

## Public interfaces
- Catalog stores such as `SpellbookStore`, `ItembookStore`, `MissionbookStore`, and `RacebookStore`
- `MenuStore` - menu JSON load/save helpers
- `ActiveBattleStore` - active battle save/load layer
- `PlayerMemoryStore` - sqlite-backed memory persistence facade

## Invariants and boundaries
- Preserve on-disk payload compatibility unless the change explicitly includes a data migration.
- Keep serialization and path handling here instead of leaking file logic into services.
- Do not place gameplay rules here; this layer stores and reconstructs data.

## File map
| Path | Responsibility |
|------|----------------|
| `menu_store.py` | Menu JSON persistence |
| `active_battle_store.py` | Active battle save/load operations |
| `character_store.py` and catalog stores | Character and content catalog persistence |
| `player_memory/` | Player memory sqlite schema, row mapping, and store facade |
| `tuning_store.py` | Tunable settings persistence |

## Tests
```bash
python -m pytest -q tests/test_active_battle_store.py tests/test_persistence_stores.py tests/test_player_memory_store.py tests/test_player_save.py
```

## Common changes
- Add a stored field: update the store, the affected domain conversion helpers, and the persistence tests together.
- Refactor path handling: preserve current `GameData` locations unless the change explicitly includes path migration.
- Debugging: reproduce with the narrow persistence test before opening service orchestration code.
