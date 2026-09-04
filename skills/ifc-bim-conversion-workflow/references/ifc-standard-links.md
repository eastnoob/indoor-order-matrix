# IFC Standards

Use these primary sources for schema semantics and validation behavior:

- [buildingSMART IFC lexical documentation](https://ifc43-docs.standards.buildingsmart.org/)
- [IfcOpenShell validation API](https://docs.ifcopenshell.org/autoapi/ifcopenshell/validate/index.html)

Treat parser success as syntax evidence only. Preserve validation errors as
blocking failures and keep warnings separate. Do not invent IFC entities,
relationships, or validator APIs beyond these sources and the installed
IfcOpenShell interface.
