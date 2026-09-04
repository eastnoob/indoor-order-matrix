# Software Preflight

Report each capability independently before using it:

| Capability | Check | Missing result |
| --- | --- | --- |
| Python/Pixi | `pixi run python --version` | `not_available`; use the selected environment or ask for setup |
| IfcOpenShell | import it in the selected Python | validation `not_available`; block import |
| Native exporter | inspect the source project's documented tools | reuse it before writing code |
| Rhino/Bonsai/Blender | confirm the target application and its official import route | `not_available` for the dependent phase |
| MCP | confirm the documented endpoint and read-only capability | `not_available`; do not claim live verification |

Do not install tools silently or alter the source model. Optional tools may be
used through the existing Pixi environment; this skill adds no runtime
dependency. For this repository, discover the existing Rhino-to-IFC adapter at
`test/bim/convert_rhino_fixture_to_ifc.py` before generating an exporter.

Preflight reports should include the selected executable/environment, detected
versions, source path, and one actionable reason for each unavailable or
blocked capability. A preflight phase does not run export, validation, import,
or verification as a side effect.
