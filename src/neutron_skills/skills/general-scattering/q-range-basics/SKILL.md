---
name: q-range-basics
description: Plan an experiment's accessible momentum-transfer (Q) range from wavelength, scattering angle, and detector geometry. Use when a user asks about choosing instrument configuration, Q_min/Q_max, or length scales probed in any neutron scattering experiment.
metadata:
  techniques: [SANS, diffraction, reflectometry, inelastic]
  tags: [Q, planning, geometry, wavelength]
---

# Q-range basics

The momentum transfer for elastic scattering is

$$ Q = \frac{4\pi}{\lambda} \sin\theta $$

where $2\theta$ is the scattering angle and $\lambda$ is the neutron wavelength.

## Typical ranges

| Technique      | Q range (Å⁻¹)        | Length scale d ≈ 2π/Q |
|----------------|-----------------------|------------------------|
| SANS           | 0.001 – 0.5           | 10 – 6000 Å            |
| Reflectometry  | 0.005 – 0.3           | surfaces / multilayers |
| Diffraction    | 0.5 – 20              | atomic bonds           |
| Inelastic      | instrument-dependent  | varies                 |

## How to pick a configuration

1. **Start from the length scale** you want to probe: $d \approx 2\pi/Q$.
2. Choose $\lambda$ compatible with the source/chopper.
3. Solve for $\theta$ (or detector distance) that puts your target $Q$
   on the detector.
4. Cross-check $Q_{min}$ from beamstop and $Q_{max}$ from detector edge.

## Common mistakes

- Forgetting that $Q_{min}$ is set by the beamstop, not just $\lambda$.
- Using too-long wavelengths when shorter $d$ also matter — you lose $Q_{max}$.
