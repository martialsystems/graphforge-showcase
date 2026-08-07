# Architecture (demo)

## Problem

Agent and CI pipelines encode process in prose and scripts. Rules like “do not
publish without review” are easy to skip under automation pressure. When the
rule is only in a README, nothing stops an illegal transition.

## Approach

Encode the allowed control flow as an explicit graph over typed state:

1. **Channels** — named state slots with reducers (last-write or append).
2. **Nodes** — steps that return partial updates.
3. **Edges** — fixed or conditional next step.
4. **Laws** — predicates run after a node; failure aborts the run (fail closed).
5. **Audit** — append-only event list of node and law outcomes.

Illegal writes to unknown channels raise. Illegal law outcomes raise
`LawViolation`. The run does not continue to publish/deploy after a failure.

## What this demo is not

- Not the commercial GraphForge engine (private product).
- No LLM runtime, checkpoints, multi-tenant catalog, or license server.
- No claim about trading, forecasts, or domain alpha.

## Package layout

```
src/lawgraph/     # tiny runtime
examples/         # agent release gate (toy domain)
tests/            # legal path + fail-closed paths
```

## Mapping to agentic systems

| Concern | Demo mechanism |
|---------|----------------|
| Agent wants to ship | `publish` node |
| Must pass tests | law on `test` |
| Must get review | law on `review_gate` |
| Skip review | `LawViolation` |
| Prove what ran | `audit_log` |

Swap the domain labels; keep the same gate pattern.
