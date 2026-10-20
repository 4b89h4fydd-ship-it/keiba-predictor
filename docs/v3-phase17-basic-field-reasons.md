# Phase 17: basic runner field reason codes

Per runner, saved-only `basicFieldReasons` independently labels each of
`name`, `jockey`, `trainer`, and `carriedWeight` as `absent`,
`null`, `placeholder`, `invalid-type-or-number`, or `saved-value`.
These are properties of the existing saved row, **not** original website
or collector provenance. An absent value must not be interpreted as debut.
The Python display transport rejects conflicting state/reason vs its allowlisted
saved row. Both racing circuits are compared with Node Worker projection.
No fetching, writes, predictions, UI changes, merge, or deploy.
