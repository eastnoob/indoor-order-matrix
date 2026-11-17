# Analysis Plane Shared Context Design

## Goal

Require every evidence-package evaluation and processing call to receive a
non-empty, immutable analysis-plane context while allowing package algorithms
to ignore that context when their declared calculation does not use it.

## Decisions

- `AnalysisPlane` remains the existing immutable fact type. It is not widened
  with domain, grid, model, cache, or UI state.
- `PackageAnalysisContext` is a small frozen value containing one or more
  ordered `AnalysisPlane` values. The first plane is the primary plane.
- Empty contexts, non-plane values, duplicate identities, and conflicting
  revisions/poses are rejected before callbacks, producers, processors, or
  cache reads run.
- A package accepts one plane by default. Multiple planes require both the
  package declaration and an explicit call-site permission. This permission is
  an execution contract, not a claim that a single-plane algorithm can use
  multiple planes.
- Context resolution never creates a projection, grid, domain, model view, or
  automatic upstream package. A callback may receive and ignore the context.
- A missing context can be adapted only from one complete, trusted source
  query plane. Calls with no trusted plane must pass context explicitly.
- Existing `AnalysisContext`, `AnalysisRequest`, `FieldQuery`, raw/processed
  v1 payloads, result references, and numerical identities remain unchanged.
- The context is call metadata. A plane that an algorithm does not use must
  not be injected into its numerical query, result provenance, or cache key.
- Native/UI settings own scene default and package overrides. They resolve a
  frozen `PackageAnalysisContext` at job start and use the same resolution for
  the request and job binding. Existing single-plane properties remain a
  compatibility mirror.
- Full native capture, source authentication, support consent, and freshness
  checks remain mandatory. Numeric cache reuse may project only verified
  physical dependencies; it may not bypass capture or consent checks.
- The implemented projection retains every external dependency, including
  saved IFC SHA. Camera-only edits within the same captured source can reuse
  numerical results; saved external byte changes conservatively miss without
  a verified IFC dependency proof. No IFC private-closure parser is added.

## Object relationships

```text
scene/UI settings -> selected AnalysisPlane values
                         |
                         v
               PackageAnalysisContext
                         |
                         v
      EvidencePackage.evaluate/process_output
                         |
                         v
      package-owned algorithm / processor / cache adapter
```

`EvidencePackage` remains a shared publication and processing template, not a
base class for all packages and not a scene or cache manager. Package entry
functions continue to own business inputs, parameter resolution, storage, and
calculation orchestration.

## Public contract

```python
@dataclass(frozen=True, slots=True)
class PackageAnalysisContext:
    planes: tuple[AnalysisPlane, ...]

    @property
    def primary_plane(self) -> AnalysisPlane: ...

class EvidencePackage:
    supports_multiple_planes: bool = False

    def evaluate(..., *, analysis_context=None,
                 allow_multiple_planes=False): ...

    def process_output(..., *, analysis_context=None,
                       allow_multiple_planes=False): ...
```

The first five positional constructor arguments and existing callback
signatures remain compatible. `EvidencePackageInput` gains a keyword-only
`analysis_context` field for context callbacks.

## Compatibility and failure behavior

- Existing single-plane callers may continue when a unique complete source
  query plane supplies the context.
- Existing no-plane fixtures and pure contracts are migrated to pass an
  explicit context without changing their serialized source bytes.
- A context mismatch that belongs to a package's real geometry/query lineage
  remains the package's responsibility; the shared resolver does not relabel
  raw evidence or enforce unrelated plane use.
- Cache hits validate the context before returning a stored result.
- Unsupported multi-plane calls fail before any numerical work.

## Verification scope

Focused tests cover frozen context validation, default and explicit selection,
multi-plane permission, callback delivery, zero numerical work when ignored,
cache-hit validation, old callback/constructor compatibility, raw/processed
wire stability, and native default/override/request-binding consistency. A
portable-Blender source-only native-camera lifecycle check has passed against
the actual IFC copy. Live UI, `.blend` restart and physical geometry
recalculation remain separate checks; see the linked verification record.
