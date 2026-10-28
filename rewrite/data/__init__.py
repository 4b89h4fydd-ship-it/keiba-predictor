"""Clean-room data foundation for the ARVEXQ rewrite.

Independent of every legacy module: no imports from ``arvexq`` or ``app``.
Pipeline: sources (raw bytes + provenance) -> normalize (field-level
missingness, leakage guard, banei exclusion) -> store (append-only raw
snapshots + normalized records) -> quality (coverage gates).
"""
