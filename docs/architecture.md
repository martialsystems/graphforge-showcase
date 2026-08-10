# Architecture (demo)

## Problem

Agent and CI pipelines encode process in prose and scripts. Rules like “do not
publish without review” or “never overwrite fresher artifacts” are easy to skip
under automation pressure. When the rule is only in a README, nothing stops an
illegal transition.

## Approach

Encode the allowed control flow as an explicit graph over typed state:

1. **Channels:** named state slots with reducers (last-write or append).
2. **Nodes:** steps that return partial updates (fully autonomous).
3. **Edges:** fixed or conditional next step.
4. **Laws:** predicates run after a node; failure aborts the run (fail closed).
5. **Budgets:** `max_steps` stops runaway loops.
6. **Audit:** hash-chained event list; `verify_audit()` detects tamper.

Illegal writes to unknown channels raise. Sealed reducers refuse writes.
Illegal law outcomes raise `LawViolation`. The run does not continue to
publish/deploy after a failure. **No human-approval node.**

## Autonomous fail-safes

| Fail-safe | Mechanism |
|-----------|-----------|
| Fail closed | `LawViolation` stops the run |
| Step budget | `max_steps` → `GraphError` + `budget_fail` audit |
| Typed state | Unknown channel → `GraphError` |
| Stale publish | Law: src track ≥ dest track |
| Tool junk | Law: required schema keys |
| Evidence | Hash-chained audit after every run |

Humans may change graphs or inputs **offline** and re-run. They are not a
runtime gate.

## What this demo is not

- Not the commercial GraphForge engine (private product).
- Not SPY/BTC domain graphs (those live in private consumers).
- No LLM runtime requirement, multi-tenant catalog, or license server.
- No claim about trading, forecasts, or domain alpha.

## Package layout

```
src/lawgraph/     # tiny runtime (state, graph, audit)
examples/         # release, pipeline, site publish, agent tool
tests/            # legal + fail-closed paths
docs/             # architecture + interview card
```

## Mapping to agentic systems

| Concern | Demo mechanism |
|---------|----------------|
| Agent wants to ship | `publish` / `apply` node |
| Must pass tests / schema | law after node |
| Tool returns junk | `tool_schema_valid` |
| Runaway tool loop | `max_steps` |
| Overwrite fresher artifact | `stale_over_fresh_block` |
| Prove what ran | hash-chained `audit_log` |

## Why not just X?

- **Scripts / if-statements.** Topology and laws are structure; illegal writes
  fail in the runtime.
- **Generic FSM libraries.** This demo centers *post-step product laws* and
  typed merges with audit of gate outcomes.
- **LangGraph / agent frameworks.** Those orchestrate LLM tool loops. This is
  process-first: whether an action is allowed. An LLM can sit *inside* a node;
  laws stay predicates.
- **OPA alone.** External policy for a request; here policy is coupled to graph
  position and channel state produced on this run.

Commercial GraphForge layers more on this idea; this repo teaches the core shape.
