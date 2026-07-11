"""Console entry surface under the public name.

Delegates to :func:`microcosm_core.cli.main`, which owns the full command
registry. Kept as its own module so packaging metadata and downstream callers
can name ``plectis.cli:main`` without reaching into the compatibility package.
"""

from microcosm_core.cli import main

__all__ = ["main"]
