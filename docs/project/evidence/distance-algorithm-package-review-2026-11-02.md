# Distance algorithm package review

Date: 2026-11-02  
Status: **Expanded to native C/C++ candidates; no backend selected; no implementation change**

## Scope correction

The first review considered Python-facing packages and prematurely recommended a Python `heapq` implementation. That conclusion was too early. The user clarified that a native C/C++ library called from Python is in scope. Language is not an exclusion criterion; the real comparison is semantic fit plus integration and maintenance cost.

The required distance semantics remain those in the design draft: 4-neighbor grid, physical non-negative edge lengths, per-access-cell centroid offsets, one source run serving all targets, observed-free and optimistic state variants, conditional dependency tracking, stable tie-breaking, and one reproducible representative path. Implicit adjacency is a memory/implementation preference, not a different distance definition; an explicit sparse graph is acceptable if its measured cost is reasonable. State/lineage may be recovered by the adapter from the selected path, and source offsets may be encoded by a virtual source. A library need not implement these domain concepts natively to qualify.

## Candidate comparison

| Candidate | Useful capability | Contract mismatch / integration cost | Assessment |
| --- | --- | --- | --- |
| `python-tcod` / modern `tcod.path.Pathfinder` | Native compiled pathfinder exposed to Python; grid-oriented graph; supports cardinal movement, multiple roots with per-root initial values, a full distance field and path tracing. Closest ready-made grid engine in this review. | Its public path cost, distance and root values are integers. The design currently uses physical floating-point distances and exact distance tie rules. A fixed-point scale could make it usable, but would introduce a declared quantization/error contract and could change close comparisons. Secondary conditional-count and stable complete-path tie rules still need project-owned handling. | **Strongest packaged implicit-grid candidate, conditional on explicitly accepting fixed-point distances and verifying tie behavior. Not selected yet.** |
| Boost.Graph (C++) | Generic Dijkstra; configurable distance comparison/combination and property maps. A custom graph model can generate grid neighbors on demand, avoiding explicit edge materialization; a virtual source can represent different access offsets. | Boost does not provide this project’s grid adapter. The project would implement a custom C++ graph/model and Python binding or C ABI, then own build and ABI maintenance. The current Pixi manifest declares no Boost, binding layer, or C++ toolchain; the current PowerShell session did not resolve `cl`, `clang++`, `g++`, or `cmake`. A custom label and path tie contract still needs careful implementation. | **Technically promising if measured performance justifies native integration; not a drop-in grid package.** |
| Legacy libtcod Dijkstra C API | Grid-oriented search with caller-defined edge cost callbacks, including floating edge costs. | Its legacy Dijkstra map has one origin per computed map; serving each access seed with a distinct offset would require repeated runs or extra project graph logic. Its callback does not supply this module’s multi-source labels, state lineage or stable tie contract. | **Not a direct fit for the batched weighted-source contract.** |
| igraph C API | Mature weighted shortest-path routines and path output; floating edge weights and a virtual source can encode access offsets. | Requires an explicit graph; compare graph construction/memory and binding cost with the alternatives. State lineage and deterministic tie recovery remain adapter work. | **Viable explicit-graph candidate; not excluded by source offsets or state metadata alone.** |
| SciPy sparse graph | Compiled weighted Dijkstra with multiple source indices and predecessor output; CSR plus a virtual source can retain floating offsets. The current Pixi environment imports SciPy 1.17.1; its source uses a C++ priority queue through Cython. | Requires a materialized sparse graph. Its returned predecessor is not a guaranteed project-stable representative; a tie-recovery pass must prove the required ordering without changing lengths. SciPy is installed transitively but not directly declared in Pixi. | **First candidate for contract verification; reuse the native kernel before writing a new search loop.** |
| NetworkX | Already declared in Pixi; weighted Dijkstra and path reconstruction. | Explicit graph and Python object overhead; no direct endpoint-offset, composite-state or stable full-path tie contract. | **Convenient diagnostic oracle on bounded IFC-derived cases, not an implicit-grid engine.** |
| Project-owned Python `heapq` | Could implement the implicit grid and project comparison/state rules without a new native build boundary. | The search loop, tie rules and numerical behavior would all be project code requiring verification and measurement. | **Provisional fallback, not a proven or selected adapter.** |

## Recommendation and decision gate

Do not reject C/C++ on language grounds. Prefer reusing a mature search kernel when the complete adapter is simpler to maintain; neither compilation nor the absence of domain metadata proves suitability by itself. No candidate’s adapter or performance has been verified on the specified IFC workload yet.

**Owner recommendation: first verify SciPy’s native Dijkstra plus a narrow adapter.** This already reuses compiled C++ search through its Python interface; using a Python API does not imply a Python search loop. Keep igraph as a second explicit-graph candidate, `python-tcod` if a fixed-point contract becomes acceptable, Boost.Graph for a justified custom native graph, and `heapq` only as a fallback. This is a candidate order, not a frozen backend choice.

The SciPy adapter must deduplicate virtual-source edges by cell before CSR construction: repeated CSR entries otherwise sum rather than select the smallest access offset. Keep the winning access provenance under the same stable ordering. Run source groups sequentially or in bounded batches rather than storing a full group-by-grid distance matrix. Recover state/lineage from the selected path. Verify conditional-count and complete-path tie ordering using shortest-distance labels instead of trusting the library’s arbitrary tied predecessor; exact floating comparisons and endpoint ordering still need a concrete, reviewed recovery procedure. This procedure is not implemented or proven by this review.

Before choosing or adding a backend, the implementation plan must state whether fixed-point quantization is allowed. If it is not, `python-tcod` cannot be adopted as the semantic backend. If performance is the only reason to add C++, compare the Python baseline and a bounded Boost prototype on the same approved IFC/query; compare exact outputs, runtime, peak memory and build/reproducibility cost. No IFC run or code spike was performed in this design-only stage.

## Primary references

- Boost.Graph Dijkstra: https://www.boost.org/doc/libs/latest/libs/graph/doc/dijkstra_shortest_paths.html
- Boost.Graph concepts: https://www.boost.org/doc/libs/latest/libs/graph/doc/graph_concepts.html
- python-tcod Pathfinder: https://python-tcod.readthedocs.io/en/latest/tcod/path.html
- python-tcod package: https://pypi.org/project/tcod/
- Legacy libtcod Dijkstra API: https://libtcod.github.io/docs/html2/path_init.html?c=true&cpp=true&cs=false&lua=false&py=false
- igraph C structural algorithms: https://igraph.org/c/html/latest/igraph-Structural.html
- SciPy sparse Dijkstra: https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.dijkstra.html
- SciPy 1.17.1 compiled shortest-path source: https://github.com/scipy/scipy/blob/v1.17.1/scipy/sparse/csgraph/_shortest_path.pyx
- NetworkX weighted shortest paths: https://networkx.org/documentation/stable/reference/algorithms/shortest_paths/weighted.html

Local verification: `pixi run python -c "import scipy; from scipy.sparse.csgraph import dijkstra; print(scipy.__version__, dijkstra.__module__)"` returned `1.17.1 scipy.sparse.csgraph._shortest_path`. No dependencies were installed or modified.
