# IFC MassPatch Multi-Representation Note

## Decision

An analysis substitute that belongs to one logical furniture product should
preferably be exported as a second shape representation of that same product:

```text
IfcFurniture
└── IfcProductDefinitionShape
    ├── Body      -> visible display geometry
    └── Analysis  -> MassPatch used by analysis
```

This preserves the semantic fact that there is one furniture occurrence. The
analysis geometry is another representation of it, not another chair or table.

## IFC vocabulary and project conventions

- `Body` is the conventional visible product representation context.
- `Analysis` is a project convention for the analysis representation role; it
  is not an IFC-standard MassPatch type or a guaranteed Bonsai display policy.
- `OM_*` properties are project-defined factual extensions. They bind source
  identity, representation role, algorithm/version facts, or other provenance;
  they are not IFC-native semantics.
- An `IfcBuildingElementProxy` sidecar is a compatibility fallback only. It is
  a separate IFC product linked by project-defined properties, not the second
  representation of the original `IfcFurniture`.

## Bonsai handoff

IFC can carry multiple representations, but it does not by itself guarantee
that Bonsai will hide every non-`Body` representation. The Bonsai adapter must
select `Body` for the default visible preview and retain `Analysis` for the
analyser or an explicitly enabled inspection view. Visibility is therefore an
adapter policy, not something inferred from the string `Analysis` alone.

## Scope of the next export change

The next change should cover only IFC export, IFC inspection, and representation
selection/reading. It must not couple MassPatch discovery or generation to the
export phase. Existing sidecar output remains available as an explicit fallback
for consumers that cannot preserve multiple shape representations.

## Acceptance facts

An accepted export must make these facts auditable:

1. The number of logical furniture occurrences is unchanged.
2. `Body` and `Analysis` resolve to the same product when multi-representation
   mode is used.
3. Sidecar mode clearly reports a separate compatibility product.
4. Bonsai visibility is verified by the selected adapter rather than assumed
   from IFC property names.
