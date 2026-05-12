---
name: rietveld-refinement-workflow
description: >
  Sanity-check a Rietveld refinement of neutron powder-diffraction data.
  Use when reviewing refinement strategy, diagnosing poor fit, setting
  parameter release order, or evaluating goodness-of-fit metrics (Rwp,
  chi-squared).
version: 2
review:
  status: human-reviewed
  reviewer: Malcolm Guthrie
  reviewed_on: 2026-05-07
  basis: [docs, code, instrument-science-review]
  notes: >
    v2: Rietveld refinement workflow with parameter release order guidance,
    goodness-of-fit metric interpretation, and software capability notes
    (GSAS-II, FullProf, TOPAS, MAUD). Clarified software notes as subset of
    popular packages; referenced asset for metric definitions and software-
    specific conventions. Skill applies to any Rietveld package and any
    neutron source type (TOF or monochromatic).
  approved_commit: review/rietveld-refinement-workflow-v2
metadata:
  techniques: [diffraction, powder-diffraction, rietveld]
  tags: [refinement, analysis, fit-quality]
---

# Rietveld Refinement Workflow

This skill guides an agent through a safe, incremental Rietveld refinement
of neutron powder-diffraction data: from data and model setup through
parameter release to a verified, publishable fit. It applies to any Rietveld
software (GSAS-II, FullProf, TOPAS) and any neutron source type (TOF or
monochromatic), with notes where behaviour differs.

Related skills:
- [sns-snap-high-pressure-data-interpretation](../sns-snap-high-pressure-data-interpretation/SKILL.md) — high-pressure sample and cell-component modelling
- [sns-snap-reduction-diagnostics](../sns-snap-reduction-diagnostics/SKILL.md) — diagnosing upstream reduction problems that corrupt the input histograms

Detailed metric reference:
- [Rietveld-quality-metrics-summary](assets/Rietveld-quality-metrics-summary.md) — profile, Bragg, and software-specific metric definitions and caveats

---

## Overview

This skill produces a converged Rietveld refinement whose goodness-of-fit
metrics are acceptable, whose difference
curve is featureless, and whose refined parameters are physically meaningful
and documented. The refinement is traceable: the instrument parameter file,
the structural model, all phases (sample + environment contributors), and the
parameter release sequence are all recorded.

**Instrument-parameter separation** — the central design constraint of
Rietveld is the separation of instrumental contributions (intrinsic peak shape, background) from sample contributions (unit
cell, atomic positions, thermal parameters, preferred orientation, absorption).
Instrumental contributions should be fixed from calibration measurements
before any sample refinement begins. Only sample contributions are refined
during the main analysis cycle.

**Dataset structure for neutron data:**
- Each histogram must be paired with an instrument parameter file describing
  instrumental contributions to peak shape and position.
- For TOF data: bank- (or pixel-group-) specific parameter files; each group
  has distinct profile parameters that must be applied independently.
- For monochromatic data: typically a single parameter although several use cases (e.g. rotating textured sample or sampling different detector regions) can generate multiple histograms.
- Multi-histogram Rietveld (10–100 histograms from different angular
  perspectives) will become increasingly common for TOF instruments such as SNAP and
  can resolve angular domains; the same parameter-separation principles apply.

**Software capability notes** — listed here are only a subset of the most popular
  Rietveld packages; the workflow principles apply to any package:
- **GSAS-II**: Widely used and accessible; originally developed for neutrons (GSAS-I legacy)
  but recent development focuses on synchrotron X-ray. Includes Python API (GSAS-II scriptable)
  for programmatic workflows. Multi-histogram TOF refinement is possible but can be cumbersome
  for even small numbers of these.
- **FullProf**: Optimized for magnetic and complex symmetry structures; provides
  strong phase-specific Bragg and structure-factor metrics; multipattern capable.
- **TOPAS**: Most flexible parametrization; supports background-corrected residuals.
  Useful when standard peak-shape or background models are insufficient.
- **MAUD**: Best for combined analysis of texture, strain, and microstructure
  alongside profile refinement; strong in multi-dataset workflows.

**Quality-metric interpretation is software-specific** — see
  [Rietveld-quality-metrics-summary](assets/Rietveld-quality-metrics-summary.md) for
  detailed definitions, software-specific conventions, and interpretation pitfalls:
- Always identify whether reported GOF/Chi2 is $R_{wp}/R_{exp}$ or
  $(R_{wp}/R_{exp})^2$ before deciding if fit quality is acceptable.
- Do not compare raw metric values across packages unless weighting,
  background handling, exclusions, and histogram aggregation are aligned.
- Profile metrics ($R_{wp}$, $R_p$) should be interpreted with residual
  curves and phase-specific metrics ($R_{Bragg}$, $R_F$, $R_{F^2}$) when available.

---

## When to Use

- Use when starting a new Rietveld refinement and setting the parameter
  release order.
- Use when a refinement has stalled, diverged, or produced unphysical
  parameters.
- Use when the difference curve shows unexplained structure.
- Use when $R_{wp}$ is high and the cause is unclear.
- Do NOT use as the reduction-stage skill — invoke
  [sns-snap-reduction-diagnostics](../sns-snap-reduction-diagnostics/SKILL.md)
  first if the input histograms are suspect.

---

## Process

Collect this context before starting:
- Reduced histogram file(s) and the matching instrument parameter file(s).
- Identity of all phases expected in the pattern (sample, pressure medium,
  calibrant, sample-environment components).
- Starting structural model(s) — note whether they are ambient
  entries; for high-pressure data, see caveats in
  [sns-snap-high-pressure-data-interpretation](../sns-snap-high-pressure-data-interpretation/SKILL.md)
  if working at pressure.
- Software package in use (GSAS-II, FullProf, TOPAS, other).
- Estimated number of independent observables and initial free-parameter
  count for the proposed model.

---

1. **Load data and instrument parameters** — Import each histogram with its
   paired instrument parameter file. For TOF data, confirm that bank- or
   group-specific parameter files are matched to the correct histograms.
   Do not begin refinement until every histogram has a correctly paired
   parameter file.

   **[CHECKPOINT]**: All histograms load without errors. Each is paired with
   the correct instrument parameter file.

2. **Build the starting model** — Define all crystallographic phases that
   contribute to the pattern: sample phase(s), any pressure medium,
   calibrant, and sample-environment components (e.g., anvil or gasket
   materials that contribute Bragg peaks). Unidentified peaks must be
   assigned to a phase before proceeding; do not start refinement with
   unexplained peaks. Optionally define excluded regions where data are contaminated or otherwise deemed unreliable.

3. **Fix all instrumental contributions from calibration** — Set peak-shape
   parameters, zero-point/sample displacement, and background from the
   instrument parameter file. Do not refine these during the sample analysis
   cycle unless there is a specific, documented reason. Instrumental
   parameters refined against sample data are a common source of physically
   meaningless results.

   **[CHECKPOINT]**: Instrumental contributions are fixed. Starting $R_{wp}$
   is recorded as the baseline before any parameter release.

4. **Validate model definition against data information content** — Confirm
   that model sophistication matches data quality before releasing any sample
   parameters.
   - Hard limit: number of free parameters must not exceed the number of
     independent observables.
   - Reduce parameter count where justified using constraints and shared
     physics (for example, rigid-body constraints for known molecular or
     polyhedral units).
   - Ensure model does not include parameters to which the data are insensitive, especially considering the Q-range of the data and corresponding limits on physical real-space resolution.
   - Prefer isotropic thermal parameters first; only escalate to anisotropic
     thermal parameters when statistics and data quality clearly support it.
   - For multi-histogram refinements of the same sample, avoid inflating per-histogram nuisance
     terms without clear residual evidence. 

   **[CHECKPOINT]**: Free-parameter count and observables are recorded, the
   hard-limit condition is satisfied, and any constraints/restraints are
   documented with rationale.

5. **Release parameters in safe order** — Release one group at a time,
   confirming convergence and inspecting the difference curve at each step
   before releasing the next group:
   1. Scale factor
   2. Zero-point / sample displacement (only if not fixed from calibration)
   3. Background (polynomial or Chebyshev — sufficient degree to describe
      the data without over-fitting)
   4. Unit-cell parameters
   5. Profile shape via package dependent models (e.g. for strain broadening,
      anisotropic size broadening, or microstrain models) — only if there is
      clear evidence of these effects in the difference curve after releasing
      the previous groups; otherwise, they can be added later as a final
      refinement stage to try to improve fit quality after all structural
      parameters are released.
   6. Preferred orientation and/or absorption corrections — only when there
      is clear evidence these effects are present
   7. Atomic positions (symmetry-allowed only)
   8. Isotropic thermal parameters ($B_{iso}$ / $U_{iso}$) — only after all positional parameters are released and the fit has
      stabilized; these parameters are strongly correlated with absorption
      and peak shape, so they should be released last among the main sample
      parameters.
   9. Anisotropic thermal parameters ($U_{ij}$) — only with high-quality data
      and adequate statistics

   Only release the next group after the fit has stabilised (parameters no
   longer shifting significantly between cycles) and $R_{wp}$ has plateaued.

6. **Inspect difference curve after each release** — The difference curve
   should approach featureless noise as the model improves. Any structure
   remaining in the difference curve after a parameter group is released
   indicates a model deficiency; see Red Flags for diagnostic guidance.
   Do not release the next parameter group to compensate for undiagnosed
   residual structure.

7. **Evaluate goodness-of-fit metrics** — After the final release cycle,
   assess both profile agreement and structural agreement using a
   package-aware interpretation:
   - $R_{wp}$: target ≤ ~10% for good neutron data; useful for monitoring
     improvement on the same dataset, but not meaningful in isolation.
   - $R_{exp}$: the statistically expected lower limit from counting
     statistics and model complexity.
   - GOF/Chi2 convention: determine whether the software reports
     $R_{wp}/R_{exp}$ or $(R_{wp}/R_{exp})^2$ before interpretation.
   - Phase-aware metrics (when available): inspect $R_{Bragg}$ and
     $R_F$/$R_{F^2}$ for structural agreement in each phase.
   - Parameter uncertainties: check that refined parameters have physically
     reasonable values and uncertainties consistent with the data quality.

   Minimum software-specific checks:
   - **GSAS-II**: inspect histogram-level residuals, not just global project
     values; check Durbin-Watson/residual-correlation diagnostics when available.
   - **FullProf**: treat reported Chi2 as commonly squared
     ($(R_{wp}/R_{exp})^2$); inspect phase-specific Bragg and RF factors.
   - **TOPAS**: do not mix primed (background-corrected) and unprimed
     residuals when comparing fits.
   - **MAUD/JANA/other multi-dataset workflows**: global metrics can hide
     poor fit in one component; inspect dataset-specific metrics.

   **[CHECKPOINT]**: The difference curve is featureless, software-specific
   metric conventions are documented, and all refined parameters are
   physically meaningful. $\chi^2 = 1.0$ is the statistical ideal, but higher
   values are normal on many instruments (e.g., where $\sigma_i$ are
   underestimated or the model is systematically limited); evaluate $\chi^2$
   relative to instrument-typical baselines rather than the absolute ideal.

8. **Document the refinement** — Record: software and version, instrument
   parameter file(s) used, all phases and their sources, parameter release
   sequence, final $R_{wp}$, $R_{exp}$, $\chi$, and any deviations from the
  standard release order with justification. Also record model-complexity
  controls (free-parameter count, observable count, and constraints used).

**Exit criteria**: Converged fit with a featureless difference curve,
physically meaningful parameters, and complete documentation. $\chi = 1.0$ is
the statistical ideal; where instrument-typical values differ, the achieved
$\chi$ should be evaluated against those instrument norms and any deviation
from 1.0 noted and justified.

---

## Rationalizations

| Rationalization | Why it is wrong |
|-----------------|-----------------|
| "I'll release several parameter groups at once to speed things up." | Simultaneous release causes parameters to compensate each other rather than converging on physical values. Strong correlations (e.g., $U_{iso}$ and absorption) make the fit unstable. Follow the release order one group at a time. |
| "The background looks roughly right, I'll release atomic positions now." | Incorrect background absorbs signal that should be Bragg intensity. Atomic positions released against a wrong background refine to compensate for it, producing unphysical coordinates. Background must be stable before positions are released. |
| "There's some structure in the difference curve but $R_{wp}$ is acceptable." | $R_{wp}$ is a sum over all data points; structured residuals at specific peaks indicate a model failure that the overall metric obscures. The difference curve must be inspected at each stage, not just at the end. |
| "I'll refine the instrument parameters against this sample data — it might improve the fit." | Instrument parameters refined against sample data absorb sample information into the instrument model. The resulting parameters are not transferable and the sample parameters are meaningless. Fix instrument contributions from calibration. |
| "Those peaks are probably noise — I don't need to assign them to a phase." | Unassigned peaks bias the background model and can cause incorrect intensity extraction for nearby sample peaks. Every visible peak must be assigned before refinement begins. |
| "Uij refinement always improves the fit." | $U_{ij}$ adds six parameters per atom. On limited statistics or poorly reduced data it produces unphysical displacement ellipsoids that inflate apparent fit quality without physical meaning. Only release if data quality justifies it. |
| "The solver converged, so parameter count does not matter." | Convergence does not imply identifiability. If free parameters exceed independent observables, the model is underdetermined and physically non-unique. Apply constraints or simplify the model before refinement. |

---

## Red Flags

- Difference curve shows a sharp peak-shaped feature after releasing profile
  parameters → incorrect peak-shape parameters or zero-point; the instrument
  parameter file may be mismatched to this histogram. Revisit steps 1 and 3.
- Difference curve shows a broad hump not explained by any assigned phase →
  unmodeled impurity phase or sample-environment contributor; inspect longest
  d-spacings first. Revisit step 2.
- $\chi \gg 1$ after full release → systematic model failure; do not release
  more parameters — diagnose residual structure in the difference curve first.
- $\chi \ll 1$ → possible over-fitting (too many free parameters for the data
  quality) or overestimated uncertainties in the input data. Review parameter
  count and data quality.
- Refined $U_{iso}$ or $U_{ij}$ values are negative or unphysically large →
  strong correlation with another parameter (commonly absorption or
  background); the data do not support this level of structural detail.
  Fix or remove the correlated parameter. Check whether the input data have
  been correctly reduced and normalized (see
  [sns-snap-reduction-diagnostics](../sns-snap-reduction-diagnostics/SKILL.md)).
- Atomic positions drift to symmetry-disallowed values → starting model is
  wrong or the unit cell has not converged; revisit step 5 order and check
  model complexity constraints in step 4.
- Fit does not converge after releasing a parameter group → too many
  parameters released simultaneously, or strong correlations between groups.
  Revert to the previous stable state, simplify the model in step 4, and then
  release one group at a time in step 5.

---

## Verification

Before marking the refinement complete:

- [ ] All histograms paired with correct instrument parameter files; loading
      confirmed without errors.
- [ ] All phases contributing to the pattern identified and included in the
      model; no unexplained peaks remain.
- [ ] Instrumental contributions fixed from calibration; not refined against
      sample data (or deviation documented with justification).
- [ ] Free-parameter count does not exceed independent observables; any
  constraints/restraints used to enforce identifiability are documented.
- [ ] Parameter release order followed; each group converged before the next
      was released.
- [ ] Difference curve is featureless (noise-like) across the full d-spacing
      range for every histogram.
- [ ] $\chi = R_{wp}/R_{exp}$ is recorded; $\chi = 1.0$ is the ideal, but
      values above 1.0 are common on many instruments — evaluate against
      instrument-typical baselines and document any deviation from 1.0 with
      justification. Both $R_{wp}$ and $R_{exp}$ are recorded.
- [ ] Software-specific metric convention is recorded (for example,
      GOF vs Chi2 definition and whether values are squared or square-root).
- [ ] Phase-aware metrics are reviewed and recorded where available
      ($R_{Bragg}$, $R_F$, $R_{F^2}$) in addition to profile metrics.
- [ ] All refined parameters are physically meaningful; uncertainties are
      consistent with data quality.
- [ ] Refinement documented: software + version, instrument parameter files,
      phases and sources, release sequence, final metrics, any deviations
      from standard order with justification.

