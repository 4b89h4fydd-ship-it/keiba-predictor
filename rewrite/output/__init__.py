"""Output adapters for the ARVEXQ rewrite.

Clean-room presentation layer: converts rewrite engine records
(``rewrite.data`` / ``rewrite.analysis``) into the payload shapes the
existing production frontend consumes. It computes nothing about the
races themselves — probabilities, marks and tickets come only from the
analysis layer — and it never invents evidence the engine does not
have (no fabricated EV, probability ranges, or receipts).
"""
