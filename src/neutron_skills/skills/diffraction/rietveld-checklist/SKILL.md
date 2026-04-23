---
name: rietveld-checklist
description: Sanity-check a Rietveld refinement of neutron powder-diffraction data. Use when reviewing refinement strategy, diagnosing poor fit, setting parameter release order, or evaluating goodness-of-fit metrics (Rwp, chi-squared).
metadata:
  techniques: [diffraction, powder-diffraction, rietveld]
  tags: [refinement, analysis, fit-quality]
---

# Rietveld refinement checklist

A safe release order for refineable parameters:

1. Scale factor
2. Zero-point / sample displacement
3. Background (polynomial or Chebyshev)
4. Unit-cell parameters
5. Profile shape (GU, GV, GW, LX, LY for GSAS-II; U, V, W, X, Y for FullProf)
6. Atomic positions (symmetry-allowed only)
7. Isotropic thermal parameters (Biso / Uiso)
8. Anisotropic thermal parameters (Uij) — only with good data
9. Preferred orientation / absorption corrections

## Diagnostics

- **Rwp**: target ≤ ~10% for good neutron data; always compare against
  Rexp — the ratio Rwp/Rexp is $\chi$.
- **Difference curve**: should look like noise, not a signature of a peak.
- **Split residuals** at individual peaks signal profile-shape or
  zero-point issues, not atomic positions.

## Common pitfalls

- Releasing atomic positions before the background is correct.
- Over-refining Uij on limited statistics (unphysical ellipsoids).
- Ignoring impurity phases — look at the longest $d$-spacings first.
