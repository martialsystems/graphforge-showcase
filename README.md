# Product-law graphs (portfolio demo)

[![tests](https://github.com/martialsystems/graphforge-showcase/actions/workflows/test.yml/badge.svg)](https://github.com/martialsystems/graphforge-showcase/actions/workflows/test.yml)

Minimal control-plane pattern for **encoding process rules as an executable
graph** so **autonomous** agent and CI pipelines **fail closed** on illegal steps.

```text
[Autonomous agent/CI]
  -> [Typed state + explicit graph]
  -> [Deterministic engine loop]
  -> [Fail-closed laws + step budget + hash audit]
```

This repository is a **portfolio / interview demo**. It is not the commercial
GraphForge product (private). Ideas match production use: typed state, laws after
nodes, mechanical fail-safes, audit of gate decisions. Private GraphForge already
verifies real SPY/BTC consumers; this repo is the teachable kernel only.

**Status:** fixed-scope demo — see [CONTRIBUTING.md](CONTRIBUTING.md).

## In production (where GraphForge actually checks)

This demo is the portable control-plane pattern only. The commercial engine
(private) verifies real research/ops consumers. Public surfaces report **pass/fail
suite checks**, not forecast skill or live trading.

| Surface | What you see | Link |
|---------|----------------|------|
| GraphForge landing | Product framing + links to suite boards | [martialsystems.net/graphforge.html](https://martialsystems.net/graphforge.html) |
| SPY suite checks | GraphForge consumer verify footprint | [martialsystems.net/spy-graphforge.html](https://martialsystems.net/spy-graphforge.html) |
| BTC 15m ops checks | GraphForge consumer verify footprint | [martialsystems.net/btc-graphforge.html](https://martialsystems.net/btc-graphforge.html) |
| SPY vol board | Research board; pipeline re-exports verification (Last checked) | [martialsystems.net/vol-forecast.html](https://martialsystems.net/vol-forecast.html) |
| Browser console demo | In-browser template laws (not this Python repo) | [martialsystems.net/graphforge-demo/](https://martialsystems.net/graphforge-demo/) |
| This repo CI | Legal + illegal gate tests | [Actions](https://github.com/martialsystems/graphforge-showcase/actions) |

SPY/BTC **graph sources stay private**. Public pages are verification footprints
and research boards, not a source distribution of GraphForge.

Interview line: public repo teaches the kernel; production GraphForge already
gates SPY and BTC consumers on the boards above.

## Why this exists

Agents and automation are good at taking actions. They are bad at respecting
unstated processes:

- publish without tests / review signal
- promote when quality failed
- overwrite a fresher artifact with a staler one
- apply junk tool JSON
- loop forever

If the rule lives only in documentation, it will be skipped. If the rule is a
**law attached to a graph node** (or a step budget), the run stops and records
the failure. **No human-in-the-loop pause.** Fail-safes are autonomous.

## Quick start

Python 3.10+.

```bash
cd graphforge-showcase
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install pytest

export PYTHONPATH=src:.

python examples/agent_release_gate.py
python examples/data_pipeline_gate.py
python examples/site_publish_gate.py
python examples/agent_tool_gate.py

pytest -q
```

## Examples

### 1. Agent release gate

```text
plan → implement → test → review_gate → publish → END
```

| After node | Law (autonomous) |
|------------|------------------|
| `test` | `tests_passed` must be true |
| `review_gate` | automated review signal must be `approved` |
| `publish` | tests + review + artifact digest |

Illegal: skip review, failed tests. See `examples/agent_release_gate.py`.

### 2. Data-pipeline promotion gate

```text
ingest → validate → stage → promote → END
```

| After node | Law |
|------------|-----|
| `validate` | schema ok and row_count > 0 |
| `stage` | quality_score >= threshold |
| `promote` | schema + quality + stage digest |

See `examples/data_pipeline_gate.py`.

### 3. Site / artifact publish (stale-over-fresh)

```text
build → compare → publish → END
```

| Fail-safe | Behavior |
|-----------|----------|
| Stale src | `src_track < dest_track` → `LawViolation`, no publish |
| Freeze | clearing `freeze_locked` on this path → fail closed |
| Audit | hash chain verifies after legal and illegal runs |

See `examples/site_publish_gate.py`.

### 4. Agent tool + step budget

```text
plan → tool_call → apply → END
```

| Fail-safe | Behavior |
|-----------|----------|
| Tool schema | partial JSON → fail before `apply` |
| `max_steps` | runaway loop → `GraphError` + `budget_fail` audit |

See `examples/agent_tool_gate.py`.

## Design notes

**Typed channels.** Nodes cannot invent state keys.

**Reducers.** Scalars use last-write; ledgers use append.

**Fail closed.** Laws raise `LawViolation`. No “warn and continue.”

**Budgets.** `run(..., max_steps=N)` stops autonomous runaway graphs.

**Audit.** Hash-chained events; `graph.verify_audit()` or `verify_audit(log)`.

Longer notes: [docs/architecture.md](docs/architecture.md).  
Interview card: [docs/INTERVIEW.md](docs/INTERVIEW.md).

## Design FAQ

| Question | Short answer |
|----------|----------------|
| Human in the loop? | No. Fail-safes are laws, budgets, sealed writes, audit. |
| Different from a script? | Topology and laws are structure; illegal writes fail in the runtime. |
| Where do LLMs fit? | Optional inside a node. Laws do not require an LLM. |
| How do you test process? | Drive illegal state; expect `LawViolation` or budget error. |
| Production? | Private GraphForge: checkpoints, multi-surface catalog/trace, SPY/BTC consumers, richer audit. |

## Scope

**In scope:** small runtime, four end-to-end autonomous gate examples, tests.

**Out of scope:** full orchestration product, hosted control plane, domain finance
graphs, open-sourcing the proprietary engine.

## License

MIT for **this demo repository only** — see [LICENSE](LICENSE).

Commercial GraphForge remains proprietary to Martial Systems LLC.

## Author

Samuel Wagner, Martial Systems LLC, 2026

Portfolio demo of the product-law control-plane pattern used in proprietary
GraphForge at Martial Systems LLC.
