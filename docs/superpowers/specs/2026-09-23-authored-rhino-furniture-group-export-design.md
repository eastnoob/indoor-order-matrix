# Authored Rhino Furniture-Group Export Design

## Goal

Export only explicitly tagged Rhino furniture-group containers as IFC
`IfcGroup` records. Their nested furniture remains individual IFC furniture
with the existing `Body` and optional `Analysis` representation contract.

## Authoring Contract

The only marker is `OM.Role = furniture_group`, placed on a Rhino Block
instance or its Block Definition. Definition User Text supplies a default;
instance User Text overrides it. A marked outer Block is a relationship
container, not an IFC product, and therefore has no IFC geometry.

No composition name, identifier, activity label, or furniture type tag is
required. Nested furniture follows its existing recognition rules. A child is
not made into a furniture member solely because it is nested in the container.

## Capture Contract

The Rhino capture script merges Definition and instance User Text, detects
only an effective `OM.Role=furniture_group`, omits the root container from the
ordinary object list, and expands its direct nested instances using composed
transforms. It emits individual furniture object records plus:

```json
{
  "furniture_groups": [
    {"id": "outer-instance-guid", "member_ids": ["derived-member-id"]}
  ]
}
```

Member ids are deterministic paths below each outer instance, so repeated
outer Block instances become separate groups and separate furniture
occurrences. Untagged Blocks and non-furniture children remain on their
pre-existing full-export path.

## IFC Contract

Each valid record creates one `IfcGroup` with
`ObjectType = "furniture_group"`, no product representation, and one
`IfcRelAssignsToGroup` to its resolved `IfcFurniture` or
`IfcFurnishingElement` members. The group identity derives from its outer
instance id.

The exporter must stop creating synthetic `IfcGroup` records from
`source_model`: source-model membership is provenance, not an authored layout
group. Missing/non-furniture member ids are omitted and reported; an empty
group is omitted and reported.

## Adapter And Skill Contract

The IFC adapter maps `IfcGroup.ObjectType == "furniture_group"` to
`AuthoredGroup.group_role == "furniture_group"`; all other IFC groups remain
`ifc_group`. Skills document the one-marker authoring rule and the fact that
there is no name/layer/proximity/geometric group inference.

## Scope And Verification

No affordance, region, path, trend, scoring, MassPatch, grid, fallback export,
or Bonsai import behavior changes. Tests cover repeated tagged groups,
unmarked/non-furniture isolation, the existing Body/Analysis contract, absence
of synthetic source-model groups, adapter role recovery, and skill wording.
All changed code uses English-first docstrings and intent comments.
