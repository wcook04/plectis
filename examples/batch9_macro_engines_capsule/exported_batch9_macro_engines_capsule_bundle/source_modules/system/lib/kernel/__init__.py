"""
[PURPOSE]
- Teleology: Package root for modularized kernel CLI internals.
- Mechanism: Re-exports state initialization so kernel.py can bootstrap cleanly.

[INTERFACE]
- Exports: init_state (from .state)

[FLOW]
- kernel.py calls init_state(repo_root) once during bootstrap, before any command.
- Command submodules import shared paths and helpers from kernel.state.
- When-needed: Open when you need the package-level kernel bootstrap entrypoint rather than reading `kernel.py` or `system/lib/kernel/state.py` directly.
- Escalates-to: system/lib/kernel/state.py; kernel.py
- Navigation-group: kernel_lib

[DEPENDENCIES]
- system.lib.kernel.state

[CONSTRAINTS]
- init_state MUST be called before any command module function is invoked.
"""
from system.lib.kernel.state import init as init_state

__all__ = ["init_state"]
