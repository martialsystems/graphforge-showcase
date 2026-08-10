# Interview walkthrough (graphforge-showcase)

**Thesis:** Autonomous pipelines still need mechanical fail-safes. Product law
is encoded as a typed graph; illegal transitions fail closed and leave an audit
chain. No human-in-the-loop node.

Commercial GraphForge (private) already gates real SPY/BTC consumers. This repo
is the portable kernel only.

## In production (open these)

| Surface | URL |
|---------|-----|
| GraphForge landing | https://martialsystems.net/graphforge.html |
| SPY suite checks | https://martialsystems.net/spy-graphforge.html |
| BTC 15m ops checks | https://martialsystems.net/btc-graphforge.html |
| SPY vol board (Last checked) | https://martialsystems.net/vol-forecast.html |
| Browser console demo | https://martialsystems.net/graphforge-demo/ |
| This demo repo | https://github.com/martialsystems/graphforge-showcase |

Do not claim those boards are “the model edge.” They show software/process checks
and research exports. Graph source remains private.

## 60-second pitch

Agents and CI are good at taking actions and bad at respecting unstated process.
I encode process as an explicit graph: typed channels, reducers, post-node laws,
hash-chained audit. The run is fully autonomous. Fail-safes are laws, step
budgets, and sealed writes—not a person approving mid-flight.

## Commands (live demo)

```bash
cd graphforge-showcase
python -m venv .venv && source .venv/bin/activate
pip install pytest
export PYTHONPATH=src:.

python examples/agent_release_gate.py
python examples/data_pipeline_gate.py
python examples/site_publish_gate.py
python examples/agent_tool_gate.py
pytest -q
```

## What to show

| Demo | Fail-safe |
|------|-----------|
| Release gate | Tests + automated review signal before publish |
| Data pipeline | Schema + quality before promote |
| Site publish | Stale-over-fresh block; freeze bit untouched |
| Agent tool | Schema-valid tool JSON; `max_steps` kills runaway loops |
| Audit | `verify_audit()` on legal and failed runs |

## Answers to common questions

**Where is the human?** Not in the graph. Recovery is a new autonomous run after
fixing inputs, the graph, or the offline freeze process—not a mid-run pause.

**How is this different from if-statements?** Topology, channel shape, and laws
are first-class. Illegal channel writes and missing edges fail in the runtime.
Tests drive illegal initial state and expect `LawViolation`.

**LLMs?** Optional inside a node. Laws stay plain predicates. This is a control
plane for *whether an action is allowed*, not a full agent framework.

**Production?** Private GraphForge adds checkpoints, multi-surface catalog/trace,
richer hash audit, packaging. SPY/BTC verification already runs there—point at
the public suite boards and vol board **Last checked** (links above), not at
this public demo’s domain graphs.

## Do not claim

- Trading edge, forecast skill, or that this is the commercial engine
- That humans never operate systems offline—only that **this runtime** has no
  human-approval step
