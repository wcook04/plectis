"""Idea-first release microcosm runtime package.

[PURPOSE]
Expose the public-safe idea microcosm Python package as the release runtime root.

[INTERFACE]
Provides package identity for CLI, builders, probes, validators, and tests.

[FLOW]
Importers enter concrete modules through idea_microcosm.cli or named builders.

[DEPENDENCIES]
Depends only on the package modules shipped inside the release microcosm.

[CONSTRAINTS]
Package presence is local runtime evidence, not public release or private-root proof.
"""

__version__ = "0.1.0"
