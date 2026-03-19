# UI Menu Models

## Purpose
`src/ui/menu` contains the shared menu model objects used by menu loading and runtime rendering.

This package is intentionally small and model-focused. It should not own Discord interactions, file IO, or menu-loading logic.

## Entry points
- Main module(s): `models.py`, `__init__.py`
- Called by: `src/services/menu_service` and `src/services/menu_runtime`

## Public interfaces
- `Menu` - menu node and option container
- `MenuContext` - mutable menu-session context state
- `ContextButton` - contextual action-button metadata
- `MenuState` - menu state enum

## Invariants and boundaries
- Keep these classes serialization-friendly and light on side effects.
- Do not move Discord response logic into this package.
- Menu JSON loading stays in persistence and service layers.

## File map
| Path | Responsibility |
|------|----------------|
| `models.py` | Menu state, menu nodes, and contextual button definitions |
| `__init__.py` | Public re-exports for menu model imports |

## Tests
```bash
python -m pytest -q tests/test_menu_runtime.py tests/test_menu_view.py
```

## Common changes
- Add a model field: update the model, then update the loader/runtime paths that consume it.
- Refactor menu state: keep import paths stable through `__init__.py`.
- Debugging: start from menu runtime tests rather than opening Discord view code first.
