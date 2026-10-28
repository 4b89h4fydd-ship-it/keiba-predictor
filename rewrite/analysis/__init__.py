"""Ability and pace analysis for the ARVEXQ rewrite.

Clean-room: consumes only ``rewrite.data`` normalized records and
produces evidence-carrying results. Composite weights are explicit,
versioned priors per race segment — they are NOT fitted parameters and
must not be presented as such until the backtest step fits and
validates them on held-out races.
"""
