# Reading an exact free-space result

Use the existing result wire and session reader in Pixi. A result document is
authoritative sample data; the Blender overlay is a display. Reading does not
capture a scene, project geometry or calculate free space.

The consuming operation supplies these inputs independently of the document it
is checking:

| Input | Meaning |
| --- | --- |
| `result_path` | `pathlib.Path` to a published result JSON, or JSON exported from its embedded Blender Text |
| `requested_ref` | Exact `kind`, `result_id`, `digest` mapping delivered by the producing operation |
| `expected_identity` | The consumer's expected project/source, domain, plane and query identity |
| `expected_backend_versions` | Complete backend mapping accepted by the consumer |
| `native_observation` | Unmodified observation retained from verified native publication |
| `row`, `column` | Integer lattice indices selected by the consumer |

For free space, `expected_identity` should include `project_source_identity`,
`domain_identity`, `plane_uuid`, `plane_revision`, `frame_key` and `query_key`.
The query is the full `GeometryQuery.to_dict()` mapping, including its height
band. Include the expected `semantic_key` to bind the remaining request semantics,
including sampling. Production identities also expose
`canonical_structural_fingerprint`, `canonical_full_fingerprint`,
`request_source_fingerprint`, `request_identity`, `domain_request_id`,
`domain_session_revision` and `operation`; supply them when the consuming
operation requires those exact identities. The opener checks every supplied
entry, but does not require a complete identity mapping. Copying expectations
from the document being checked cannot establish that it is the desired result.

```python
from adapters.blender_analysis_result_wire import (
    ResultRef, ResultReadContext, list_analysis_results, load_json,
    open_analysis_result,
)
from adapters.blender_analysis_session import read_analysis_sample

documents = [load_json(result_path.read_text(encoding="utf-8"))]
result_ref = ResultRef(**requested_ref)
catalogue = list_analysis_results(documents, kind="free_space_run")
assert result_ref in tuple(item.ref for item in catalogue)

# Keep consumer expectations and native evidence separate from stored result data.
context = ResultReadContext(
    expected=expected_identity,
    backend_versions=expected_backend_versions,
    require_confirmed_domain=True,
    require_current=True,
    current_observation=native_observation,
)
snapshot = open_analysis_result(documents, result_ref=result_ref, context=context)
sample = read_analysis_sample(snapshot, row=row, column=column)
assert snapshot.freshness == "current"
```

The catalogue is discovery metadata, not a latest-result selector. An absent,
ambiguous or mismatched exact ref raises `ValueError`, as do mismatched expected
identity/backend versions and a missing confirmed-domain binding. A current
read additionally requires the observation's digest and complete binding to
match this exact publication. Do not catch these failures and treat another
result as current.

`sample` is the immutable `FieldSample`: retain `value`, `status`, `query`,
`support`, `source_ids`, `provenance` and `explanation`. The value describes
physical occupancy: `True` means occupied and `False` means known empty, not a
walkability or clearance claim. `unknown` has `value=None`; `conditional`
retains its value and representation explanation. Freshness does not upgrade a
field status. `outside`, `invalid` and `not_available` are also distinct exact
status names.
`support` can be `None`; do not assume every state has a support mapping.
Object boundary contact is a participation-audit relation, not another field
status and not automatic positive-area cell occupancy.

## Receiving the native observation

After successful verified publication, the existing native runtime exposes the
observation. Use the same registered add-on instance that performed publication.
The installed add-on is `order_analyzer_ui`, with runtime
`order_analyzer_ui.runtime`; importing the checkout under
`blender_addon.order_analyzer_ui` can create a separate idle `STATE`. In the
producing Blender session, retain the existing value:

```python
from order_analyzer_ui import runtime
from adapters.blender_analysis_result_wire import plain

assert runtime.__name__ == "order_analyzer_ui.runtime"
assert runtime.STATE.lifecycle == "complete"
assert runtime.STATE.freshness == "current"
assert runtime.STATE.current_observation is not None
native_observation = plain(runtime.STATE.current_observation)
```

Deliver that observation separately with the exact published ref and the
verification run's source/session identity, time and artifact hashes. Do not
construct a verified flag or copy a stored document binding into an observation.
The runtime creates its observation only after the publication's native guards
pass. A headless reader trusts that external verification; it cannot reobserve
Blender by reading JSON. A retained observation establishes the recorded
verification instant, not live currentness after later scene edits.

## Cache hits and restored documents

A cache hit publishes a new result with the current job/request/domain-session
binding and a new exact ref. Use that publication's independently retained
observation in the same reader example. The public
`snapshot.payload["content_cache"]` reports `hit`, `content_key` and, on a hit,
`origin_result_ref`; the origin identifies the reused calculation, not the
current publication. Sample calculation provenance and any unknown/conditional
limitations remain intact. The new publication's observation cannot authorize
its origin ref as current. Use a published sidecar or embedded document, not an
internal content-cache entry, as the downstream handoff.

Restoring JSON from disk or Blender Text alone is historical. For an explicit
diagnostic read of the requested ref, use:

```python
historical = open_analysis_result(
    documents,
    result_ref=result_ref,
    context=ResultReadContext(
        expected=expected_identity,
        backend_versions=expected_backend_versions,
        require_confirmed_domain=True,
        allow_historical=True,
    ),
)
assert historical.freshness == "historical"
historical_sample = read_analysis_sample(historical, row=row, column=column)
```

This read supplies no native observation. Setting `require_current=True` for
restored bytes without fresh matching evidence must reject. Restored native
workflows must establish their own current publication before current use.

Existing consumer, cache and complete-sample contracts are in
`test/test_blender_analysis_session.py`; native publication and edit guards are
in `test/test_blender_analysis_runtime.py`. Actual-scene acceptance and its
unobserved branches are recorded separately in the free-space prerequisite
evidence ledger; this guide does not certify a particular result.
