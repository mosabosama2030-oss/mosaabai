# MOSAABAI_AGENT_CONTRACT.md v1.0.0

Authoritative execution contract for any AI agent operating on the MosaabAI repository.

Subordinate to MOSAABAI_MASTER_v1.0.5 and to any valid Executive Order.

## 1. AGENT MAY
- Read any file in the repository
- Read AGENTS.md and this contract
- Read the current Executive Order
- Create branch: feat/<task-id> or fix/<task-id>
- Modify files within the EO's declared allowed_paths
- Run pytest -v
- Run ruff check on changed files
- Commit with message specified in the EO
- Push the branch to origin
- Open a Pull Request to main
- Produce an evidence package at .evidence/EO-XXX.json

## 2. AGENT MAY NOT
- Modify files outside the EO's allowed_paths
- Redefine acceptance criteria
- Expand the scope of the EO
- Bypass CI checks
- Merge any PR (only Human Director may merge)
- Modify .github/workflows/ unless the EO authorizes it
- Modify pyproject.toml unless the EO authorizes it
- Modify this contract or MOSAABAI_MASTER
- Introduce dependencies not listed in the EO
- Use paid APIs without approval
- Include secrets, credentials, or tokens in any commit

## 3. REQUIRED BEHAVIOR
Before executing:
1. Read this contract
2. Read the Executive Order
3. Verify current branch state (git status, git log --oneline -5)
4. Confirm baseline tests pass: pytest -v

During execution:
5. Modify ONLY files in allowed_paths
6. After each file: run ruff check <file>
7. After all files: run pytest -v

After execution:
8. Report git status, git diff --stat, full pytest output, ruff output
9. Produce .evidence/EO-XXX.json
10. Push branch, open PR
11. STOP. Do not merge.

## 4. EVIDENCE PACKAGE FORMAT
Every EO produces .evidence/EO-XXX.json with:
- task_id, base_sha, head_sha, changed_files
- agent, provider, model
- tests_run, test_result, lint_result
- invariant_results, security_result, timestamp

## 5. VALIDATION GATES
Every PR must pass:
1. GATE 0 - Authority: Valid EO exists
2. GATE 1 - Contract: Agent read this file
3. GATE 2 - Scope: Only allowed_paths modified
4. GATE 3 - Regression: pytest passes, zero regressions
5. GATE 4 - Lint: ruff check clean on changed files
6. GATE 5 - Invariants: Applicable invariants tested
7. GATE 6 - Security: No secrets, no unauthorized deps
8. GATE 7 - Evidence: .evidence/EO-XXX.json present
9. GATE 8 - Audit: Independent review
10. GATE 9 - Authorization: Human Director approves
11. GATE 10 - Merge: Only Human Director merges

## 6. SEMANTIC EQUIVALENCE STANDARD
Acceptance requires:
- Same behavior (pytest golden vectors pass)
- Same invariants preserved
- Same ruff compliance

Not required:
- Same code style, variable names, or commit messages

## 7. TERMINATION CONDITIONS
Agent MUST stop and report if:
- Required files are outside allowed_paths
- Baseline tests fail before starting
- Any test fails twice
- Task requires modifying this contract
- Task requires paid services not approved
- Ambiguity in the EO

---
Signed: ChatGPT, Gemini, DeepSeek, Human Director
