# AGENTS.md

You are a coding agent working in this repository. Optimize for:
- minimal file reads (3–5 files per typical task)
- SOLID OOP design
- clean, navigable structure
- accurate, up-to-date README docs

## Hard boundaries
- Never print, log, or commit secrets (keys, tokens, passwords, private credentials).
- Do not modify generated code, vendored code, or build artifacts unless explicitly asked.
- Save files (`*.json`, `*.csv`) are data assets; do not “refactor” them.

## Code quality rules (mandatory)
- Target 150–400 lines per file. Soft limit: 600. Refactor candidate: 800+.
- Target 20–50 lines per function. Review 80+. Avoid 150+ unless very uniform.
- One responsibility per file.
- Keep interfaces small and dependencies shallow.
- Separate orchestration, logic, helpers, and side effects.
- Avoid god classes, hidden state, and vague names.
- A typical task should require reading only 3–5 files.

Exceptions:
- Generated code
- Enum/constants/schema files
- Save files (`*.json`, `*.csv`)

## Repo commands (fill in during discovery)
- Install: UNSPECIFIED
- Run game: UNSPECIFIED
- Lint/format: UNSPECIFIED
- Typecheck: UNSPECIFIED
- Tests: UNSPECIFIED

## Navigation protocol (doc-first, then targeted deep-dive)
1) Read `/README.md` first.
2) If the task touches a subsystem folder, read that folder’s `README.md` next.
3) Only then open code files:
   - start at an entry point (CLI/game runner) or a test that covers the behavior
   - follow imports/callers
4) Prefer opening a small set of relevant files over grep-reading everything.

## Summarize vs deep-dive rules
- Summarize when mapping a directory or deciding what to open next.
- Deep-dive only when you are about to edit or when a behavior is ambiguous.

## README maintenance triggers
Update root README and relevant subsystem README(s) when:
- entry points change (new/renamed runners, CLI, bootstraps)
- build/test/lint/typecheck commands change
- public interfaces change (APIs, CLI flags, config keys)
- subsystem responsibilities change (file moves across folders, new subsystem)

Skip README updates only if:
- no commands/paths/interfaces/responsibilities changed.

## Copy/paste prompts (agent self-check)
- "List the docs you loaded and the commands you plan to run."
- "Before editing code, list the 3–5 files that should be sufficient for this task and why."
- "After changes, list which README sections need updates and apply them."
