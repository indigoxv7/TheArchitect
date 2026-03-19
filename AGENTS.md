# AGENTS.md

You are a coding agent working in this repository. Optimize for:
- minimal file reads (3-5 files per typical task)
- SOLID OOP design
- clean, navigable structure
- accurate, up-to-date README docs

## Hard boundaries
- Never print, log, or commit secrets.
- Do not modify generated code, vendored code, or build artifacts unless explicitly asked.
- Treat `GameData/**/*.json` and `GameData/**/*.csv` as data assets, not refactor targets.

## Code quality rules
- Target 150-400 lines per file. Soft limit: 600. Refactor candidate: 800+.
- Target 20-50 lines per function. Review 80+. Avoid 150+ unless highly uniform.
- Keep one clear responsibility per file.
- Keep interfaces small and dependencies shallow.
- Separate orchestration, logic, helpers, and side effects.
- Avoid god classes, hidden state, and vague names.
- A typical task should be understandable from 3-5 related files.

Exceptions:
- generated code
- enum/constants/schema files
- data assets under `GameData`

## Repo commands
- Install: `python -m pip install -r requirements-dev.txt`
- Run game: `python main.py`
- Tests: `python -m pytest -q`
- Lint: `python -m ruff check .`
- Format: `python -m ruff format .`
- Typecheck: `python -m mypy main.py src tools tests`

## Navigation protocol
1. Read `/README.md` first.
2. If the task touches a subsystem folder, read that folder's `README.md` next.
3. Only then open code files:
   - start at an entry point, service facade, or relevant test
   - follow imports and callers
4. Prefer a small targeted read set over repo-wide grepping.

## README maintenance triggers
Update the root README and the relevant subsystem README when:
- entry points change
- commands change
- public interfaces change
- subsystem responsibilities move
- required environment variables change

Skip README updates only if no commands, paths, interfaces, or responsibilities changed.

## Self-check prompts
- "List the docs you loaded and the commands you plan to run."
- "Before editing code, list the 3-5 files that should be sufficient for this task and why."
- "After changes, list which README sections changed and update them."
