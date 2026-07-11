"""Plectis: the public import and module name for the Plectis toolkit.

The implementation lives in ``microcosm_core``, retained as a compatibility
surface from the project's former name (Microcosm became Plectis, June 2026).
New integrations should import ``plectis``; existing ``microcosm_core``
imports keep working unchanged.
"""

from microcosm_core import __version__

__all__ = ["__version__"]
