"""
[PURPOSE]
- Teleology: Mark the Polymarket package as the market-intelligence entrypoint for the Polymarket scan tool.
- Mechanism: Keep the package surface minimal and route readers straight to the concrete module that owns execution.

[INTERFACE]
- Exports: None from the package root; the executable surface lives in `tools/polymarket/polymarket.py`.
- Outputs: None.

[FLOW]
- Importers land on the package root.
- Readers escalate to the concrete module for actor logic, scoring, and envelope shape.

[DEPENDENCIES]
- None.

[CONSTRAINTS]
- Non-goal: This package root does not re-export `run` or `StandardActor`; it is a routing stub only.
- When-needed: Open when a caller lands on the package root and needs the next concrete Polymarket market-intelligence surface.
- Escalates-to: tools/polymarket/polymarket.py::run
- Navigation-group: market_intelligence
"""
