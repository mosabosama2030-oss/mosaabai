# MosaabAI v0.2 — Sovereign Cognitive Agent OS

**Understand → Model → Plan → Execute → Observe → Evaluate → Replan → Verify → Learn → Answer**

## Status

**Phase 0.2 — Foundation+** (improved rewrite)

| Component | Status |
|-----------|--------|
| Cognitive Loop | Working stages (injectable) |
| Error Envelope | Bounded + silent truncation (I-011) |
| WAL | Bounded payloads + auto-compact (I-011) |
| Tool Identity | Canonical `tool_id` (fixes F-002 / I-005) |
| Tool Environment | Identity-based monotonic delegation |
| Governance | Permissions + Risk engines |
| Memory | Working / Episodic / Semantic |
| Tests | 158 passing |

## What's new in v0.2

1. **Canonical Tool Identity** — `tool_id = sha256(name|version|schema)`. Same-name substitution attacks are rejected.
2. **TrustedToolRegistry** — source of truth for known-good tool identities.
3. **WAL bounds** — intent/result/error size limits + automatic compaction.
4. **Real Cognitive Loop stages** — stages write to WorkingMemory and produce structured outcomes.
5. **Injectable stage handlers** — replace any stage without touching the orchestrator.
6. **Stronger ErrorCode set** — includes `capability_violation` and `identity_failure`.

## Quick start

```bash
pip install -e ".[dev]"
pytest -v
```

```python
import asyncio
from core.cognitive_loop import CognitiveLoop

async def main():
    loop = CognitiveLoop()
    result = await loop.run("plan a research roadmap")
    print(result.success, result.answer)

asyncio.run(main())
```

## Architecture

```
core/           CognitiveLoop, WAL, Error envelope
cognition/      Strategies, planning, reasoning, world model
memory/         Working, episodic, semantic
tools/          Interface + identity, environment, built-ins
governance/     Permissions, risk
tests/          158 unit + adversarial tests
```

## Governance

See `MOSAABAI_AGENT_CONTRACT.md` and `AGENTS.md`.

- Agents open PRs only; Human Director merges.
- 11 validation gates before merge.
- Invariants: I-001, I-005, I-008, I-011, I-012, I-014, I-020.

## License

MIT
