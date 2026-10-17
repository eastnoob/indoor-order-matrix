# D6 pairwise channel run_002 repair_v4 status contract note

The input contract separates domain-record presence, usable geometry references, and geometry validity. For the fixture with a present `AnalysisDomain` record but missing geometry:

- `geometry_status = missing`
- `reason_code = missing_domain_geometry`
- diagnostic, candidate, profile, connectivity, component, and topology statuses are `not_available`
- aggregate qualification decision is `DEFERRED`

Missing input is not serialized as `invalid`. The repair uses only the existing contract vocabulary and does not add a unified API enum. The fixture frame remains display-only and is not promoted to an `AnalysisDomain`.

STOP FOR PAIRWISE CHANNEL RUN_002 REPAIR V4 REVIEW
