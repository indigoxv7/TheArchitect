# Modularization Plan

## Goals
- Keep files short and purpose-specific.
- Separate domain logic from Discord transport/UI.
- Make game logic testable without Discord objects.
- Minimize global mutable state.

## Target Package Layout

```
src/
  app/
    bootstrap.py           # startup wiring
    config.py              # env/config loading
  bot/
    commands/
      menu_commands.py     # /menu, /play
      admin_commands.py    # /set ...
    views/
      menu_view.py         # discord.ui.View + buttons
  domain/
    Character.py
    CharacterUtil.py
    Items.py
    Spells.py
    faction_functions.py
    player_functions.py
  services/
    game_context.py        # shared mutable runtime state object
    player_service.py      # player lifecycle orchestration
    menu_service.py        # menu rendering/navigation orchestration
    menu_runtime_service.py# interface/display update orchestration
    whitelist_service.py   # admin whitelist orchestration
  persistence/
    menu_store.py          # menu JSON loading
    roster_store.py        # existing-player roster and save discovery
    whitelist_store.py     # admin whitelist file handling
```

## Current State Assessment
- `main.py` is a small bootstrap/command registration entrypoint.
- Runtime mutable state is centralized in `GameContext` and injected into services.
- Remaining root-level duplicate domain files were removed after migration into `src/domain`.
- Persistence concerns for whitelist/roster/menu loading are moved into `src/persistence` store modules.

## Refactor Phases

### Phase 1 (Completed)
- Remove hardcoded menu fallback builders from runtime.
- Remove hardcoded test-player fallback startup.
- Move core modules into package structure and keep root compatibility shims.

### Phase 2 (Completed)
- Flatten package path to `src/*` (removed `src/thearchitect/*`).
- Extract from `main.py` into dedicated modules without behavior changes:
  - `src/services/player_service.py`
  - `src/services/menu_service.py`
  - `src/services/menu_runtime_service.py`
  - `src/services/whitelist_service.py`
  - `src/bot/views/menu_view.py`

### Phase 3 (Completed)
- Introduce `GameContext` object for mutable runtime state.
- Remove compatibility globals/wrappers in `main.py` and use dependency injection.
- Update integration tooling/tests to explicit service APIs.

### Phase 4 (Completed)
- Move remaining root domain files into `src/domain`:
  - `Character.py`, `CharacterUtil.py`, `Items.py`, `faction_functions.py`, `Spells.py`.
- Add persistence stores and refactor services to use them where applicable:
  - `src/persistence/whitelist_store.py`
  - `src/persistence/roster_store.py`
  - `src/persistence/menu_store.py`
- Add persistence unit tests:
  - `tests/test_persistence_stores.py`
- Keep backward compatibility for legacy save module paths via alias mapping in `src/domain/player_functions.py`.

## Code Style/OO Rules
- One class/module = one responsibility.
- Domain entities (Player/Character/Item) should not import Discord packages.
- I/O boundaries (Discord, JSON files) stay in bot/persistence layers.
- Services orchestrate domain objects and depend on interfaces, not globals.

## Acceptance Criteria
- `main.py` remains a small bootstrap and command registration entrypoint.
- New features are added by touching service/domain modules with minimal bot UI changes.
- Tests run without Discord network access.
