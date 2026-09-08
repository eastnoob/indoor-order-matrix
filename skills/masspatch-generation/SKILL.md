---
name: masspatch-generation
description: Use when explicit user intent requests generation of analysis-oriented MassPatch geometry from source geometry.
---

# MassPatch Generation

This skill exposes the existing backend generator as an independent producer.
It creates analysis-oriented geometry only when generation is explicitly requested
by the caller. It does not discover authored substitutes or export IFC, and it
does not import into Bonsai or score a layout.
It does not export IFC.

The implementation is the project backend in
`features/mass_patch_generation.py`; this skill must not duplicate its geometry
algorithm. Generated output remains separate from visible source geometry and
may be passed to another skill explicitly.
