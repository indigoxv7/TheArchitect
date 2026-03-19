# Config and Tuning

## Purpose
`src/config` owns shared configuration constants and the tuning registry used by combat, simulation, and menu rendering.

This package should provide stable access points for configuration and tunable values. The data itself lives in `GameData/Tuning`, not in scattered service call sites.

## Entry points
- Main module(s): `__init__.py`, `tuning.py`
- Called by: `main.py`, combat services, damage calculation, menu rendering, and admin tuning tools

## Public interfaces
- `EMOJI_PLACEHOLDERS` / `NANO_EMOJI` - shared emoji constants used by menus and text replacement
- `configure_tuning_directory` / `get_tuning_registry` - tuning bootstrap and registry access
- `battle_factor`, `character_stat_factor`, `misc_factor` and integer variants - hot-path helpers for retrieving tuned values

## Invariants and boundaries
- Keep hardcoded shared constants small and explicit.
- Keep live tuning definitions centralized in `tuning.py`.
- Do not duplicate tuning defaults in call sites when a schema-backed key already exists.

## File map
| Path | Responsibility |
|------|----------------|
| `__init__.py` | Shared exported constants and emoji placeholder map |
| `tuning.py` | Tuning schema, registry, cache, and typed lookup helpers |

## Tests
```bash
python -m pytest -q tests/test_tuning_settings.py tests/test_menu_view.py
```

## Common changes
- Add a tuning field: update `tuning.py`, then verify the related service test and tuning tests still pass.
- Change a shared emoji/config constant: update the callers that render it, especially menu-related tests.
- Debugging: start with `tests/test_tuning_settings.py` before following the tuning call chain across services.
