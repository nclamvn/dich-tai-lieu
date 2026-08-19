"""Translation-quality evaluation harness (TIP-Q0).

Named ``evalkit`` (not ``eval``) to avoid shadowing the Python builtin ``eval``.
Import surface is kept import-side-effect free so tests and the CLI can pull
individual pieces without triggering network or engine imports.
"""

__all__ = ["scorers", "runner"]
