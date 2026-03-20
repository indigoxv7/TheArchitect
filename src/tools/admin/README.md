# Admin Editor

## Purpose
`src/tools/admin` contains the Tkinter-based admin editor used to inspect and edit game content, players, characters, tuning, and simulation tools.

This package owns editor UI composition and local editor workflows. It should go through services for business logic and persistence rather than manipulating data files directly.

## Entry points
- Main module(s): `app.py`, `threading.py`
- Called by: `main.py`

## Public interfaces
- `start_admin_gui_thread` - boot the admin editor alongside the Discord bot
- `AdminEditorApp` - Tkinter shell that hosts feature frames
- `features/` - per-editor screens for content and tooling
- `shared/` - dialogs, pickers, scrolling, and reusable UI helpers

## Invariants and boundaries
- Keep business rules in services and domain models, not in widget callbacks.
- Reuse shared dialogs and pickers before adding one-off widget logic.
- Keep editor screens bounded by feature area rather than creating one global mega-frame.

## File map
| Path | Responsibility |
|------|----------------|
| `app.py` | Admin shell, home screen, and frame switching |
| `threading.py` | Start the Tkinter app on a background thread |
| `features/` | Feature-specific editors such as characters, missions, units, environment, and map testing |
| `shared/` | Shared UI helpers, dialogs, pickers, and scrolling infrastructure |
| `context.py` | Service bundle passed into the editor shell |

## Tests
```bash
python -m pytest -q tests/test_integration_tools.py
```

## Common changes
- Add an editor screen: wire it through `app.py`, give it a feature-local module, and reuse shared helpers where possible.
- Refactor a feature frame: separate widget layout from service calls and keep save/load orchestration explicit.
- Debugging: start from the feature frame plus `tests/test_integration_tools.py` before touching shared UI helpers.
