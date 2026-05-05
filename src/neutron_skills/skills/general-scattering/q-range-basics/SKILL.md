---
name: q-range-basics
description: Plan an experiment's accessible momentum-transfer (Q) range from wavelength, scattering angle, and detector geometry. Use when a user asks about choosing instrument configuration, Q_min/Q_max, or length scales probed in any neutron scattering experiment.
version: 2
review:
  status: pending
  reviewer: null
  reviewed_on: null
  basis: []
  notes: >
    v2: restructured to required skill anatomy (Overview / When to Use /
    Process / Rationalizations / Red Flags / Verification). Existing technical
    content retained and reorganized.
  approved_commit: null
metadata:
  techniques: [SANS, diffraction, reflectometry, inelastic]
  tags: [Q, planning, geometry, wavelength]
---

# Q-range basics

## Overview

The momentum transfer for elastic scattering is

$$ Q = \frac{4\pi}{\lambda} \sin\theta $$

where $2\theta$ is the scattering angle and $\lambda$ is the neutron wavelength.

## When to Use

Use this skill when:

- You need to estimate accessible $Q_{min}$ and $Q_{max}$ for an experiment.
- You are choosing wavelength, detector geometry, or scattering-angle coverage.
- You need to convert between target real-space length scales and Q range.

Do not use this skill when:

- You need instrument-control scripting details for data acquisition.
- You need detailed reduction or fitting guidance.

## Process

1. Start from the real-space length scale of interest using $d \approx 2\pi/Q$.
2. Choose candidate wavelength bands compatible with the source/chopper setup.
3. Estimate scattering-angle coverage and solve for expected Q reach.
4. Cross-check low-Q and high-Q limits against beamstop and detector edges.
5. Confirm the chosen setup still covers all required science length scales.

### Typical ranges

| Technique      | Q range (Å⁻¹)        | Length scale d ≈ 2π/Q |
|----------------|-----------------------|------------------------|
| SANS           | 0.001 – 0.5           | 10 – 6000 Å            |
| Reflectometry  | 0.005 – 0.3           | surfaces / multilayers |
| Diffraction    | 0.5 – 20              | atomic bonds           |
| Inelastic      | instrument-dependent  | varies                 |

### Configuration checklist

1. **Start from the length scale** you want to probe: $d \approx 2\pi/Q$.
2. Choose $\lambda$ compatible with the source/chopper.
3. Solve for $\theta$ (or detector distance) that puts your target $Q$
   on the detector.
4. Cross-check $Q_{min}$ from beamstop and $Q_{max}$ from detector edge.

### Available tools (when bound)

If the agent has tools bound from this skill's `scripts/tools.py`, use them
for concrete numeric work:

- `compute_q(theta_deg, wavelength_aa)` — Q from θ and λ.
- `compute_d_spacing(q_inv_aa)` — real-space length scale $d \approx 2\pi/Q$.
- `half_angle(two_theta_deg)` — convert 2θ to θ before calling `compute_q`.

## Rationalizations

| Excuse | Rebuttal |
|--------|----------|
| "I can estimate Q in my head and skip explicit checks." | Small mistakes in angle or wavelength assumptions propagate directly into the accessible Q window and can miss the science target entirely. |
| "Beamstop only affects beamline setup, not science planning." | Beamstop geometry directly sets practical $Q_{min}$ and therefore the largest resolvable length scales. |
| "A single wavelength choice is enough for all target length scales." | Wider science goals often require balancing low-Q and high-Q coverage that may not be reachable with one wavelength/configuration. |

## Red Flags

- Forgetting that $Q_{min}$ is set by the beamstop, not just $\lambda$.
- Using only long wavelengths when short-$d$ features are important, reducing
  achievable $Q_{max}$.
- Solving Q limits without checking actual detector-angle boundaries.
- Mixing up $\theta$ and $2\theta$ in calculations.

## Verification

- [ ] Target length scales are mapped to required Q range.
- [ ] Candidate wavelength and angle coverage are explicitly stated.
- [ ] $Q_{min}$ and $Q_{max}$ are both cross-checked against geometry
      constraints.
- [ ] Any assumptions about beamstop or detector limits are documented.
