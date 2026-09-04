# Bonsai Workflow

Use these primary sources for Bonsai project loading and Blender MCP context:

- [Bonsai documentation](https://docs.bonsaibim.org/)
- [Bonsai project/import reference](https://docs.bonsaibim.org/reference/general/topbar.html)
- [Blender MCP Server documentation](https://www.blender.org/lab/mcp-server/)

Bonsai verification requires an active `IfcStore` file and non-zero integer
`BIMObjectProperties.ifc_definition_id` mappings. A mesh imported as geometry
or merely named like an IFC class is not BIM evidence. Manual import is
non-mutating; automatic import is allowed only after immediate confirmation.
Live MCP verification is pending, so report that limitation explicitly.
