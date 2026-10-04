# AGENTS.md — MosaabAI Project Instructions

## Project
MosaabAI: Sovereign Cognitive Agent OS.
Repo: github.com/mosabosama2030-oss/mosaabai

## Conventions
- Python 3.11+ | Type hints | Docstrings (Google style)
- Pydantic only where already used
- @dataclass(frozen=True) for value objects
- No print() in library code

## Testing
- pytest for all tests
- Zero regressions required
- Bounded fields: message <=1000 chars, context <=10 keys
- Silent truncation, never raise during bounding

## Git
- Branch: feat/<task-id> or fix/<task-id>
- Never commit directly to main
- Human Director merges PRs

## Process
1. Read Executive Order
2. Verify baseline tests pass
3. Modify ONLY allowed_paths
4. Run pytest -v and ruff check
5. Push branch, open PR
6. STOP. Do not merge.

## Invariants
I-001, I-005, I-008, I-011, I-012, I-014, I-020
