# Product-law graphs (portfolio demo)

Minimal control-plane pattern for **encoding process rules as an executable
graph** so agent and CI pipelines **fail closed** on illegal steps.

This repository is a **portfolio / interview demo**. It is not the commercial
GraphForge product (that engine is private and proprietary). The ideas here are
the ones I use in production systems: typed state, explicit topology, laws after
nodes, audit of gate decisions.

## Why this exists

Agents and automation are good at taking actions. They are bad at respecting
unstated processes:

- publish without review
- promote a build when tests failed
- write to channels that should be sealed

If the rule lives only in documentation, it will be skipped. If the rule is a
**law attached to a graph node**, the run stops and records the failure.

## Quick start

Python 3.10+.

```bash
cd graphforge-showcase
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install pytest

# legal path + two illegal paths (prints what failed)
PYTHONPATH=src:. python examples/agent_release_gate.py

# tests
PYTHONPATH=src:. pytest -q
```

## Example: agent release gate

Domain is deliberately boring (not finance-specific):

```text
plan → implement → test → review_gate → publish → END
```

Laws:

| After node | Law |
|------------|-----|
| `test` | `tests_passed` must be true |
| `review_gate` | `review_status` must be `approved` |
| `publish` | tests + review + artifact digest required |

`examples/agent_release_gate.py` runs:

1. **Legal path:** tests pass, review approves, publish succeeds.
2. **Illegal path:** agent leaves review `pending` → `LawViolation`.
3. **Illegal path:** tests failed → `LawViolation` at `test`.

Core runtime is under `src/lawgraph/` (~200 lines): channels, reducers, graph
runner, laws, audit log.

## Design notes

**Typed channels.** Nodes cannot invent state keys. Unknown channel writes raise.

**Reducers.** Scalars use last-write; ledgers use append. That keeps audit-style
lists honest.

**Fail closed.** Laws raise `LawViolation`. There is no “warn and continue”
path in this demo.

**Audit.** Each successful law and node is recorded on `graph.audit_log` for
post-mortem or interview walkthrough.

Longer notes: [docs/architecture.md](docs/architecture.md).

## What interviewers usually ask

| Question | Short answer |
|----------|----------------|
| How is this different from a script? | Topology and laws are data/structure; illegal edges and state writes are rejected by the runtime, not by hope. |
| Where do LLMs fit? | Optional inside a node. Verification laws do not require an LLM. |
| How do you test process? | Same as unit tests: drive illegal initial state, expect `LawViolation`. |
| Production? | Commercial GraphForge (private) adds checkpoints, interrupts, packaging, multi-app catalog/trace, hash-chained audit, etc. This repo is the teachable core only. |

## Scope

**In scope**

- Small graph runtime
- One end-to-end agent-style gate example
- Tests for legal and illegal paths

**Out of scope**

- Full orchestration product
- Hosted control plane
- Open-sourcing the proprietary engine

## License

MIT for **this demo repository only** — see [LICENSE](LICENSE).

Commercial GraphForge remains proprietary to Martial Systems LLC and is not
published here.

## Author

Samuel Wagner, Martial Systems LLC, 2026
Built to showcase a recruiter-friendly version of the proprietary GraphForge, I am working on @ Martial Systems LLC. 
