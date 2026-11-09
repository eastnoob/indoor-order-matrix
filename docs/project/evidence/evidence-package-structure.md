# Evidence Package Structure

An evidence package groups several related evidence channels for the same
target and analysis snapshot. The package keeps shared identity and freshness;
each channel owns its own calculation and result.

```text
Evidence package
├── Package information
│   ├── target and analysis scope
│   ├── input snapshot and versions
│   └── package freshness
├── Evidence channels
│   ├── Channel A: algorithm, inputs, result, units, status, provenance
│   └── Channel B: algorithm, inputs, result, units, status, provenance
└── Visualization manifest (when the package publishes views)
```

Think of the package as a folder for one analysis result. The folder says what
was analyzed and whether that saved result is still current. Each channel is a
separate result inside it; channels do not share one calculation just because
they are in the same package.

One package can use a published channel from another package. It records which
package, output, target and channel it read, then adds its own derived channel.
The original channel remains unchanged. A fresh source can be used with its
original channel status; a stale source remains visible for audit but cannot be
used as current numeric input. This is an optional shared capability, not a
claim that current potential results already consume distance results.

The dependency reference is part of the consuming package's output identity.
The shared core does not keep a package registry: a caller validating a chain
must provide the complete package dependency graph to the cycle checker.
