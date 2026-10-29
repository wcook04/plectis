# MCP Tool Authority Replay

> **In plain terms.** Changes an automated assistant makes with outside tools should be approved and reversible. This component is given made-up records of tool use, a read-only lookup, a ticket update that changes data and an untrusted source of results. It checks each call for a declared tool, stated permissions and, for any change, that an approval and a way to undo it are recorded. It accepts or rejects each call, for example rejecting an approved change with no way to undo it. One small decision step, the accept or reject call, is checked by a mathematical proof against written rules.

This replay validates synthetic MCP-like tool records. The fixture describes a read-only lookup, a write-capable ticket update, and an untrusted result source. The validator connects declared tools and calls to scope, approval, side-effect, rollback, and instruction/data boundary references, then checks the recorded replay evidence.

An approved write without a rollback receipt is rejected; tests also reject calls to undeclared tools and side effects without authority references. The result is a check of these synthetic records, not a live MCP account test, credential certification, or a general security benchmark.

## Run the example

From the repository root with Python 3.11 or newer, run the supplied fixture into ignored local output:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.mcp_tool_authority_replay run \
  --input fixtures/first_wave/mcp_tool_authority_replay/input \
  --out .microcosm/component-guides/mcp_tool_authority_replay/out \
  --acceptance-out .microcosm/component-guides/mcp_tool_authority_replay/acceptance.json
```

The supplied fixture prints `pass` when its tool records and expected refusals satisfy the validator.

The design draws on least-privilege ideas in [Saltzer and Schroeder](https://www.cs.virginia.edu/~evans/cs551/saltzer/) and [MCP security guidance](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices).

## Verification

The replay calls a [Dafny-verified tool-call decision core](../formal/components/mcp_authority/README.md). Each accepted call requires nonempty scope, argument-hash, source-capsule, instruction/data-split and cold-replay references. Writes and external mutations also require an approval reference other than empty, `missing` or `not_required`, plus nonempty ledger and rollback references. The positive batch accepts exactly three allowed calls with one qualifying write and one untrusted-result call. Python trims textual references and treats other types as empty before supplying them to the core. The proof checks recorded metadata; it does not establish that references resolve, approvals are authentic or actions occurred.

The direct fixture calls this core. `make component-replays` separately applies the [shared admission check](../formal/replay/README.md) to the component replay’s captured observations.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/mcp_tool_authority_replay.py) and [fixture inputs](../fixtures/first_wave/mcp_tool_authority_replay/input/).
- [Tests](../tests/test_mcp_tool_authority_replay.py).
- [Saved example result](../receipts/first_wave/mcp_tool_authority_replay/mcp_tool_authority_replay_result.json) (historical, not a fresh run).
- [Component JSON record](./mcp_tool_authority_replay.json) and [canonical capsule](../core/paper_module_capsules.json).
