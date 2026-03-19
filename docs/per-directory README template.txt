# <Subsystem Name>

## Purpose
<2-5 lines. State what this subsystem owns and what it must not own.>

## Entry points
- Main module(s): <path(s)>
- Called by: <who imports or invokes this subsystem>

## Public interfaces
- Primary classes/functions intended for use by other subsystems:
  - <symbol> - <one-line responsibility>
- Key data types/constants:
  - <symbol> - <one-line responsibility>

## Invariants and boundaries
- <rule 1>
- <rule 2>
- <forbidden coupling or side effect>

## File map
| Path | Responsibility |
|------|----------------|
| <file> | <one line> |
| <file> | <one line> |

## Tests
```bash
<exact subsystem-scoped test command>
```

## Common changes
- Add feature: <where to start and which tests to update>
- Refactor: <what to preserve and where to verify>
- Debugging: <best entry point or test to reproduce behavior>
