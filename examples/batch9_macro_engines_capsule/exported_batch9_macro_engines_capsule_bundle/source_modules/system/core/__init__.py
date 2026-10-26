"""
[PURPOSE]
- Teleology: Mark `system.core` as the runtime kernel package that owns loading, governance, execution, and run-state recovery surfaces.
- Mechanism: Package boundary only; concrete behavior lives in sibling modules such as `loader`, `governance`, `engine`, and `forensics`.

[INTERFACE]
- Exports: Package marker only.
- Non-goal: Does not implement runtime behavior itself.

[FLOW]
- When-needed: Open when an agent has localized a task to `system.core` and needs the package-level map before choosing the concrete core surface to read.
- Escalates-to: system/core/loader.py; system/core/governance.py; system/core/engine.py; system/core/forensics.py
- Navigation-group: system_core

[DEPENDENCIES]
- None.

[CONSTRAINTS]
- Guarantee: Keeps package-level routing lightweight and points callers at the concrete core modules instead of duplicating their contracts here.
"""
