# Architecture (demo)

## Problem

Agent and CI pipelines encode process in prose and scripts. Rules like “do not
publish without review” are easy to skip under automation pressure. When the
rule is only in a README, nothing stops an illegal transition.

## Approach

Encode the allowed control flow as an explicit graph over typed state:

1. **Channels:** named state slots with reducers (last-write or append).
2. **Nodes:** steps that return partial updates.
3. **Edges:** fixed or conditional next step.
4. **Laws:** predicates run after a node; failure aborts the run (fail closed).
5. **Audit:** append-only event list of node and law outcomes.

Illegal writes to unknown channels raise. Illegal law outcomes raise
`LawViolation`. The run does not continue to publish/deploy after a failure.

## What this demo is not

- Not the commercial GraphForge engine (private product).
- No LLM runtime, checkpoints, multi-tenant catalog, or license server.
- No claim about trading, forecasts, or domain alpha.

## Package layout

```
src/lawgraph/     # tiny runtime
examples/         # release gate + data-pipeline promotion gate
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

## Why not just X?

Critics often ask why this is not “just” some other tool. Short answers:

- **A pile of if-statements / a script.** Works until topology and gates
  grow. Here, allowed steps, state shape, and laws are first-class structure.
  Illegal channel writes and missing edges fail in the runtime, not only when
  someone remembered the right branch.

- **A generic state-machine library.** FSMs encode transitions well; they
  rarely encode *typed state merges* and *post-step product laws* as the main
  unit. This demo is oriented around “after this node, these invariants must
  hold or the run dies,” with an audit trail of gate outcomes.

- **LangGraph / agent frameworks.** Those are excellent for LLM tool loops,
  memory, and multi-agent orchestration. This demo is deliberately smaller
  and process-first: the graph is a control plane for *whether an action is
  allowed*, not a full agent runtime. You can put an LLM *inside* a node;
  laws stay plain predicates.

- **Policy engines / OPA alone.** External policy engines decide allow/deny
  for a request. This pattern couples policy to *graph position* (after which
  step) and to *channel state produced by prior nodes*, so “publish only if
  review_status was approved on this run” is natural. Complementary, not a
  substitute for every org-wide policy use case.

The commercial GraphForge product (private) layers more on this idea;
this repo only teaches the core shape.
