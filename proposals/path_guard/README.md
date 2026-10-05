# Path Guard Proposal (S2-E)

## Purpose

Fail CI when a commit changes files outside a declared `allowed_paths` whitelist.
This enforces EO allowed_paths discipline mechanically.

## Proposed files

| Path | Status |
|------|--------|
| `proposals/path_guard/check_paths.py.proposed` | Proposal script (this PR) |
| `scripts/check_paths.py` | **NOT created** — Human Director promotes after review |
| `.github/workflows/path-guard.yml` | **NOT created** — Human Director wires CI |

## Suggested CI wiring

Create `.github/workflows/path-guard.yml` (Human Director only):

```yaml
name: Path Guard
on:
  pull_request:
    branches: ["**"]
  push:
    branches: ["**"]
jobs:
  path-guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run path guard
        run: |
          python scripts/check_paths.py \
            --config .github/allowed_paths.yaml \
            --base "${{ github.event.pull_request.base.sha || github.event.before }}" \
            --head "${{ github.sha }}"
```

## Config example (`.github/allowed_paths.yaml`)

```yaml
allowed_paths:
  - governance/
  - tools/spawn.py
  - core/security_exceptions.py
  - tests/
  - proposals/
```

## Behaviors

- Renames treated as delete + add
- Symlinks (mode 120000) rejected
- Submodules (mode 160000) rejected
- Paths containing `..` rejected
