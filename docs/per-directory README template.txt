# <Subsystem Name>

## Purpose
<2–5 lines. State what this subsystem owns and what it must not own.>

## Entry points
- Main module(s): <path(s) or UNSPECIFIED>
- Called by: <who imports/calls this subsystem>

## Public interfaces
- Primary classes/functions intended for use by other subsystems:
  - <symbol> — <one line>
- Key data types/constants:
  - <symbol> — <one line>

## Invariants and boundaries
- <rule 1>
- <rule 2>
- <imports that are forbidden, if any>

## File map
| Path | Responsibility |
|------|----------------|
| <file> | <one line> |
| <file> | <one line> |

## Tests
```bash
<exact test command scoped to this subsystem or UNSPECIFIED>
