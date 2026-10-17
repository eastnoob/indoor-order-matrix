# S3 Perturbation Audit

Status: `design_only`; formulas came from the existing probe, not production `Field` or evaluator code.

## Command

```powershell
@'<in-memory perturbation script>'@ | pixi run python -
```

The script imported `scripts/design/group_level/run_self_description_competition_probe.py` and read `scripts/design/group_level/self_description_competition_fixtures.json`.

## Results

Five executable checks passed:

- Input order and ID renaming preserved channel observations after removing expected identifier/provenance differences.
- Translation by `(17.25, -8.5)` preserved observations at `1e-10` rounding.
- A 90-degree rotation preserved geometry relations for the wall-free `geometry_conflict` fixture.
- `closed wall -> declared opening` changed only the space barrier observation (`blocked -> opening`) and candidate status (`space_conflict -> computed`); geometry and semantic observations stayed unchanged.
- `domain=true -> false` preserved geometry and produced `domain_status=not_available`, `space_support=0.0`; it did not create known-free evidence.

The deterministic base replay hash was `08e2397374ad3f0cdf05df41039d0b2eeae15bb47d44777d52bf16b5510e8410`.

## Blocked / Design-Only

- `invalid geometry -> missing geometry`: the fixture has `status=invalid` but no distinct missing-geometry representation. Removing the status makes the probe compute geometry, so the required `invalid != missing/unknown` transition cannot be verified.
- Rotation with a wall channel: walls only support vertical `x` plus `y_range`; there is no rotated wall representation.
- `z=1.6 m` eye-height versus whole-height: the fixture is 2D `XY` only and contains no `z`, height-band, or whole-height channel. No upgrade to whole-height can therefore be claimed.

No production files, tests, docs, or fixtures were modified. No `git add`, commit, or push was performed.
