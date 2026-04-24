---
name: refl1d-model-script
description: >
  Write a refl1d Python model script (a `problem.py` file) that loads neutron
  reflectometry data, builds a layered sample, and defines a `FitProblem`
  that refl1d/bumps can fit. Covers the three common fitting cases
  (single combined file, multi-segment co-refinement, multi-sample
  co-refinement), parameter-range conventions, and the QProbe / make_probe
  APIs. USE FOR: drafting a new model script or reviewing one. DO NOT USE
  FOR: running the fit itself or reducing raw data to R vs Q.
allowed-tools: Read Write
metadata:
  author: Mat Doucet
  version: "1.0"
  techniques: [reflectometry, neutron-reflectometry]
  tags: [refl1d, bumps, model, fitting, python]
---

# Writing a refl1d Model Script

A refl1d model script is a plain Python file that, when imported, exposes a
module-level variable named **`problem`** of type
`bumps.fitproblem.FitProblem`. Everything else — how you build the sample,
load the data, and wire up the probe — is up to you, but a few patterns
are strongly preferred for maintainability and co-refinement.

See also: the [neutron-reflectometry](../SKILL.md) skill for baseline
domain knowledge (SLD values, χ² interpretation, roughness rules).

## The three fitting cases

| Case | Input files | Probe | Output |
|------|-------------|-------|--------|
| 1 | One combined file (columns: `Q, R, dR, dQ`) | `QProbe(Q, dQ, data=(R, dR))` | `FitProblem(experiment)` |
| 2 | Several partial-segment files from one measurement, each with a different incident angle θ | `make_probe(T, dT, L, dL, ...)` per segment | One `sample`, N `probe`s, each wrapped in its own `Experiment`; `FitProblem([exp1, exp2, ...])` sharing `sample` |
| 3 | Several combined files from different measurements of related samples | `QProbe` per file | N independent samples + experiments, with shared parameters tied explicitly; `FitProblem([exp1, exp2, ...])` |

Detect the case from the data file naming or the user's description:

- A single `*_combined_data_auto.txt` → **case 1**.
- Multiple `*_partial.txt` files that share a `set_id` → **case 2**.
- Multiple `*_combined_data_auto.txt` files with **different** `set_id`s
  → **case 3**.

## Required script anatomy

Every refl1d script should end with a `FitProblem` assigned to `problem`.
A minimal case-1 template:

```python
"""Refl1d model for <sample description>.

Data file: <path>
"""

import os
import numpy as np
from bumps.fitproblem import FitProblem
from bumps.parameter import Parameter
from refl1d.names import SLD, Experiment, QProbe


# --- Materials ------------------------------------------------------------
# SLD in units of 1e-6 / A^2
D2O = SLD(name="D2O", rho=6.19)
Si  = SLD(name="Si",  rho=2.07)
Ti  = SLD(name="Ti",  rho=-1.95)
Cu  = SLD(name="Cu",  rho=6.40)
CuOx = SLD(name="CuOx", rho=5.0)


# --- Experiment builder ---------------------------------------------------
def create_fit_experiment(q, dq, data, errors):
    """Build one refl1d Experiment from arrays of Q, dQ (FWHM), R, dR."""
    # refl1d expects sigma (1-sigma); REF_L files store FWHM → convert.
    dq_sigma = dq / 2.355
    probe = QProbe(q, dq_sigma, data=(data, errors))

    probe.intensity = Parameter(value=1.0, name="intensity")
    probe.intensity.range(0.95, 1.05)

    # Stack order is ALWAYS substrate | ... | ambient in refl1d.
    # The leftmost operand of `|` is the substrate; the rightmost is the
    # ambient (incident medium). refl1d's default
    # Set probe.back_reflectivity to True for the case where incident beam comes from the substrate side. Otherwise False.
    probe.back_reflectivity = True

    sample = (
        Si
        | Ti(35, 5)
        | Cu(500, 5)
        | CuOx(30, 10)
        | D2O(0, 10)
    )

    # Fit ranges — tweak bounds to your sample.
    sample["CuOx"].thickness.range(5, 100)
    sample["CuOx"].material.rho.range(3.0, 7.0)
    sample["CuOx"].interface.range(1.0, 25.0)

    sample["Cu"].thickness.range(250, 800)
    sample["Cu"].material.rho.range(5.0, 7.5)
    sample["Cu"].interface.range(1.0, 15.0)

    sample["Ti"].thickness.range(10, 80)
    sample["Ti"].material.rho.range(-3.0, 1.0)
    sample["Ti"].interface.range(1.0, 15.0)

    sample["Si"].interface.range(1.0, 15.0)
    # Interface between the top-most film and the ambient lives on that
    # film's `.interface` (here CuOx); the ambient slab (D2O) has no
    # outward interface to fit.

    return Experiment(probe=probe, sample=sample)


# --- Load data & build problem -------------------------------------------
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
data_file = os.path.join(DATA_DIR, "REFL_226642_combined_data_auto.txt")

# REF_L combined file columns: Q, R, dR, dQ
q, r, dr, dq = np.loadtxt(data_file).T
experiment = create_fit_experiment(q, dq, r, dr)

problem = FitProblem(experiment)
```

## Case 2 — multi-segment co-refinement

One **physical sample** is measured at several incident angles θ. Build
one `sample` (shared across segments) and one `probe` per segment, each
built with `make_probe` so the wavelength & angular resolution are
preserved.

```python
from refl1d.names import make_probe

def create_probe(data_file, theta):
    q, data, errors, dq = np.loadtxt(data_file).T
    wl = 4 * np.pi * np.sin(np.pi / 180 * theta) / q
    dT = dq / q * np.tan(np.pi / 180 * theta) * 180 / np.pi
    dL = 0 * q  # wavelength resolution captured in dQ already

    probe = make_probe(
        T=theta, dT=dT, L=wl, dL=dL,
        data=(data, errors),
        radiation="neutron",
        resolution="uniform",
    )
    probe.intensity = Parameter(value=1.0, name=f"intensity_{theta}")
    probe.intensity.range(0.95, 1.05)
    # Optional nuisance parameters, shared across segments if desired:
    # probe.theta_offset      = Parameter(0.0, name="theta_offset").range(-0.02, 0.02)
    # probe.sample_broadening = Parameter(0.0, name="sample_broadening").range(0.0, 0.05)
    return probe

def create_sample():
    sample = Si | Ti(35, 5) | Cu(500, 5) | CuOx(30, 10) | D2O(0, 10)
    # Set ranges here, exactly once, so all experiments share them.
    sample["Cu"].thickness.range(250, 800)
    sample["Cu"].material.rho.range(5.0, 7.5)
    # ...
    return sample

sample = create_sample()
probe1 = create_probe(os.path.join(DATA_DIR, "REFL_226642_1_226642_partial.txt"), theta=0.45)
probe2 = create_probe(os.path.join(DATA_DIR, "REFL_226642_2_226643_partial.txt"), theta=1.20)
probe3 = create_probe(os.path.join(DATA_DIR, "REFL_226642_3_226644_partial.txt"), theta=3.50)

experiments = [
    Experiment(probe=probe1, sample=sample),
    Experiment(probe=probe2, sample=sample),
    Experiment(probe=probe3, sample=sample),
]
problem = FitProblem(experiments)
```

Because every `Experiment` holds the **same `sample` object**, their
layer parameters are automatically tied — no manual constraint lines
needed.

## Case 3 — multi-sample co-refinement with shared parameters

Several different measurements, each with its own sample stack, but you
want some layer parameters **tied** across them (e.g. the buried Cu/Ti
adhesion layers are physically the same; only the top oxide differs).

```python
def create_fit_experiment(q, dq, data, errors, label):
    """As case 1, but every call builds an INDEPENDENT sample."""
    # ... identical to case 1, but unique parameter names per experiment ...
    return experiment

q1, r1, dr1, dq1 = np.loadtxt(file1).T
q2, r2, dr2, dq2 = np.loadtxt(file2).T
experiment  = create_fit_experiment(q1, dq1, r1, dr1, label="A")
experiment2 = create_fit_experiment(q2, dq2, r2, dr2, label="B")

# Tie shared structural parameters: buried layers are physically shared.
experiment2.sample["Cu"].thickness    = experiment.sample["Cu"].thickness
experiment2.sample["Cu"].material.rho = experiment.sample["Cu"].material.rho
experiment2.sample["Cu"].interface    = experiment.sample["Cu"].interface
experiment2.sample["Ti"].thickness    = experiment.sample["Ti"].thickness
experiment2.sample["Ti"].material.rho = experiment.sample["Ti"].material.rho
experiment2.sample["Ti"].interface    = experiment.sample["Ti"].interface

problem = FitProblem([experiment, experiment2])
```

**What to share, what to leave free:**

- **Share** structural params of buried layers (Cu, Ti): thickness, SLD,
  interface roughness.
- **Do not share** `probe.intensity` (each measurement has its own
  normalization).
- **Do not share** the ambient SLD if the solvent differs between runs.
- **Do not share** layers whose physics actually differs (e.g. a growing
  native oxide).

Each assignment `experimentN.sample[...].x = experiment.sample[...].x`
replaces the RHS parameter into the Nth sample — afterwards there is a
single `Parameter` object seen by bumps.

## Parameter-range conventions

These bounds are good defaults; tighten them if you have prior knowledge.

| Quantity | Typical range |
|---|---|
| Layer thickness (supported film) | 5 Å – 1000 Å; never below 5 Å |
| Adhesion layer thickness (Ti, Cr) | 10 Å – 80 Å |
| Layer SLD | nominal ± 2 × 10⁻⁶ Å⁻² (±3 for adhesion / oxide layers) |
| Layer interface (roughness) | 1 Å – 30 Å, and always < ½ × min(adjacent layer thickness) |
| `probe.intensity` | 0.95 – 1.05 |
| `probe.theta_offset` | −0.02° – +0.02° |
| `probe.sample_broadening` | 0 – 0.05 |

Other rules of thumb from the [neutron-reflectometry](../SKILL.md) skill:

- Never fit the substrate SLD (treat Si, Al₂O₃, quartz as known).
- Don't add a native SiO₂ layer unless the description calls for it.
- Stack order is **substrate → ambient** when writing
  `substrate | L1 | L2 | ... | ambient`. The leftmost operand is the
  substrate, the rightmost is the incident medium.

## Common mistakes

1. **Forgetting `dq → sigma` conversion.** REF_L data files store `dQ`
   as FWHM. `QProbe` expects 1-σ. Divide by 2.355.
2. **Setting `.range()` twice.** The last `.range()` wins, but it's a
   code smell — set each parameter's range exactly once, in the builder.
3. **No `problem` variable.** The script imports, runs, but `bumps`
   reports "no fit problem found". The module must end with
   `problem = FitProblem(...)`.
4. **Absolute data paths.** Use `DATA_DIR = os.path.dirname(__file__)`
   (or an explicit `DATA_DIR = "..."` constant) so the script runs
   anywhere.
5. **Sharing parameters by name string instead of by object.** Assigning
   `experiment2.sample["Cu"].thickness = "Cu.thickness"` does nothing
   useful. Always assign the **Parameter object** from the first
   experiment.

## Validating the script

Before launching a long fit:

```bash
python -c "import runpy; runpy.run_path('model.py', run_name='__main__')"
# or, with refl1d/bumps installed:
refl1d --preview model.py
```

A successful preview plots the initial model against the data without
fitting — useful to catch layer-order bugs and obvious SLD mistakes.
