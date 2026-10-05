#!/usr/bin/env python3
"""Blocking structural validator for MosaabAI EO evidence artifacts."""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".evidence"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = {"task_id","base_sha","head_sha","changed_files","agent","provider","model_id","tests_run","test_result","lint_result","invariant_results","security_result","timestamp","audit_token"}
RESULTS = {"PASS", "FAIL", "UNKNOWN"}

def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)

def validate(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{path}: invalid JSON: {exc}")
    if not isinstance(data, dict):
        fail(f"{path}: root must be an object")
    missing = REQUIRED - data.keys()
    extra = data.keys() - REQUIRED
    if missing:
        fail(f"{path}: missing fields: {sorted(missing)}")
    if extra:
        fail(f"{path}: unexpected fields: {sorted(extra)}")
    for field in ("base_sha", "head_sha"):
        if not isinstance(data[field], str) or not SHA40.fullmatch(data[field]):
            fail(f"{path}: {field} must be a 40-char lowercase SHA-1")
    if not isinstance(data["changed_files"], list) or not all(isinstance(x, str) for x in data["changed_files"]):
        fail(f"{path}: changed_files must be a string array")
    if not isinstance(data["tests_run"], list) or not all(isinstance(x, str) for x in data["tests_run"]):
        fail(f"{path}: tests_run must be a string array")
    for field in ("test_result", "lint_result", "security_result"):
        if data[field] not in RESULTS:
            fail(f"{path}: {field} must be one of {sorted(RESULTS)}")
    if not isinstance(data["invariant_results"], dict):
        fail(f"{path}: invariant_results must be an object")
    try:
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        fail(f"{path}: timestamp must be ISO-8601 date-time")
    token = data["audit_token"]
    if token is not None:
        if not isinstance(token, dict):
            fail(f"{path}: audit_token must be null or an object")
        required = {"signer", "algorithm", "key_fingerprint", "signature"}
        if set(token) != required:
            fail(f"{path}: audit_token fields must be exactly {sorted(required)}")
        if token["signer"] != "Gemini" or token["algorithm"] != "GPG":
            fail(f"{path}: audit_token signer/algorithm mismatch")
        if not all(isinstance(token[k], str) and token[k] for k in required):
            fail(f"{path}: audit_token fields must be non-empty strings")

def main() -> int:
    files = sorted(EVIDENCE.glob("EO-*.json"))
    if not files:
        print("WARN: no .evidence/EO-*.json artifacts found (informational only at this stage)")
        return 0
    for path in files:
        validate(path)
    print(f"PASS: structurally validated {len(files)} evidence artifact(s)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
