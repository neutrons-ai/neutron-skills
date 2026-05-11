# Quality Metrics Used in Rietveld Refinement Packages

Rietveld refinement packages report several numerical metrics intended to describe the agreement between observed and calculated diffraction data. These metrics are useful, but they are not interchangeable, and their interpretation depends strongly on weighting schemes, background treatment, counting statistics, constraints, and software-specific conventions.

The most important distinction is between **profile metrics**, which measure agreement between the full observed and calculated diffraction pattern, and **structure/intensity metrics**, which measure agreement between extracted or model-derived Bragg intensities or structure factors.

---

## 1. The Least-Squares Quantity Being Minimized

Most Rietveld refinements minimize a weighted least-squares quantity of the form:

\[
S = \sum_i w_i \left(y_i^{obs} - y_i^{calc}\right)^2
\]

where:

- \(y_i^{obs}\) is the observed intensity at point \(i\)
- \(y_i^{calc}\) is the calculated intensity at point \(i\)
- \(w_i\) is the statistical weight, often approximately \(1/\sigma_i^2\)

The most statistically meaningful profile metrics are derived from this weighted residual.

---

## 2. Profile R-Factors

### 2.1 Weighted Profile R-Factor: \(R_{wp}\)

\[
R_{wp} =
\left[
\frac{\sum_i w_i (y_i^{obs} - y_i^{calc})^2}
{\sum_i w_i (y_i^{obs})^2}
\right]^{1/2}
\]

\(R_{wp}\) is usually the most important profile R-factor because it is directly related to the quantity minimized during refinement.

#### Advantages

- Closely tied to the least-squares target function.
- Useful for monitoring refinement progress on the same dataset.
- Sensitive to statistically weighted mismatch between observed and calculated profiles.

#### Pitfalls

- Not an absolute measure of structural correctness.
- Can be deceptively low if the background dominates the pattern.
- Can be deceptively low for noisy or low-count data.
- Can be high for excellent data if the model has small systematic errors.
- Strongly affected by weighting scheme, excluded regions, and preprocessing.
- Difficult to compare directly between different instruments, datasets, or software packages.

---

### 2.2 Profile R-Factor: \(R_p\)

A common form is:

\[
R_p =
\frac{\sum_i |y_i^{obs} - y_i^{calc}|}
{\sum_i y_i^{obs}}
\]

This is an unweighted profile residual.

#### Advantages

- Simple and intuitive.
- Easy to understand as a direct profile mismatch.

#### Pitfalls

- Not directly connected to the least-squares function being minimized.
- Gives all points equal treatment regardless of uncertainty.
- Strongly influenced by intense peaks and background.
- Usually less informative than \(R_{wp}\).

In practice, \(R_p\) is often reported for completeness, but \(R_{wp}\) is usually more meaningful.

---

## 3. Expected R-Factor: \(R_{exp}\)

\[
R_{exp} =
\left[
\frac{N - P}
{\sum_i w_i (y_i^{obs})^2}
\right]^{1/2}
\]

where:

- \(N\) is the number of observations
- \(P\) is the number of refined parameters

Some software packages modify this definition depending on how they handle constraints, restraints, background points, multiple histograms, or non-profile contributions.

#### Advantages

- Provides the statistically expected lower limit for \(R_{wp}\).
- Needed to interpret goodness-of-fit or reduced chi-squared values.
- Useful for determining whether the fit residual is consistent with the assigned uncertainties.

#### Pitfalls

- Only meaningful if the weights and uncertainties are meaningful.
- Can be distorted by incorrect counting statistics.
- Can be affected by how the program counts parameters, constraints, restraints, and observations.
- Not directly a measure of structural quality.

---

## 4. Goodness of Fit, Reduced Chi-Squared, and \(\chi^2\)

A common definition is:

\[
\chi^2_{red} =
\frac{R_{wp}^2}{R_{exp}^2}
=
\frac{\sum_i w_i (y_i^{obs} - y_i^{calc})^2}{N-P}
\]

Many Rietveld programs report this as **Chi2**, **\(\chi^2\)**, **reduced chi-squared**, **GOF**, or **goodness of fit**.

However, there is an important nomenclature issue:

\[
GOF = \frac{R_{wp}}{R_{exp}}
\]

while

\[
\chi^2 = \left(\frac{R_{wp}}{R_{exp}}\right)^2
\]

Some packages report the squared value, while others report the square root. This means that one program’s `GOF = 1.4` may correspond to another program’s `Chi2 = 2.0`.

#### Advantages

- Useful for judging whether the fit is statistically consistent with the assigned uncertainties.
- Helpful for comparing refinements of the same dataset.
- Ideally, reduced \(\chi^2\) should approach 1 for a correct model with correct uncertainties.

#### Pitfalls

- \(\chi^2 \approx 1\) does not prove that the structural model is correct.
- Low values can result from overestimated errors, high background, low statistics, or inappropriate weights.
- High values can result from excellent statistics revealing tiny systematic errors.
- Different packages may report either \(R_{wp}/R_{exp}\) or \((R_{wp}/R_{exp})^2\).
- Multiple datasets, restraints, constraints, and background terms may be included differently by different programs.

---

## 5. Bragg and Structure-Factor R-Factors

Profile metrics describe the agreement between the full observed and calculated pattern. They do not directly isolate the quality of the crystallographic model. For that, many programs also report Bragg or structure-factor residuals.

### 5.1 Bragg R-Factor: \(R_{Bragg}\)

A common conceptual form is:

\[
R_{Bragg} =
\frac{\sum_k |I_k^{obs} - I_k^{calc}|}
{\sum_k I_k^{obs}}
\]

where \(I_k\) refers to the integrated intensity of reflection \(k\).

#### Advantages

- More directly related to crystallographic intensities than \(R_{wp}\).
- Less dominated by background and peak-shape agreement.
- Useful for judging the quality of the structural model.

#### Pitfalls

- In powder diffraction, observed integrated intensities are often model-dependent.
- Peak overlap can make extracted intensities ambiguous.
- Preferred orientation, microstructure, absorption, and background errors can affect the apparent Bragg intensities.
- A good \(R_{Bragg}\) does not guarantee a good profile fit.

---

### 5.2 Structure-Factor R-Factors: \(R_F\) and \(R_{F^2}\)

These compare observed and calculated structure-factor amplitudes or squared amplitudes.

Conceptually:

\[
R_F =
\frac{\sum_k |F_k^{obs} - F_k^{calc}|}
{\sum_k |F_k^{obs}|}
\]

or

\[
R_{F^2} =
\frac{\sum_k |F_k^{obs2} - F_k^{calc2}|}
{\sum_k F_k^{obs2}}
\]

#### Advantages

- Closer to conventional crystallographic residuals.
- Useful for comparing structural models.
- Can be especially relevant in packages that combine powder and single-crystal data.

#### Pitfalls

- Not usually the quantity minimized in Rietveld refinement.
- Depends on how observed intensities or structure factors are extracted.
- Strongly affected by overlapping peaks.
- May look acceptable even when the profile fit is poor.

---

## 6. Difference Curves and Residual Inspection

The most important diagnostic is often not a single number, but the residual curve:

\[
y_i^{obs} - y_i^{calc}
\]

or a weighted residual.

#### Advantages

- Reveals systematic errors that scalar metrics hide.
- Helps diagnose:
  - incorrect background
  - missing phases
  - wrong peak shape
  - lattice parameter errors
  - preferred orientation
  - anisotropic strain
  - absorption errors
  - detector/calibration artifacts

#### Pitfalls

- Qualitative unless combined with other diagnostics.
- Plot scaling can visually exaggerate or hide problems.
- A visually good residual can still mask incorrect structural parameters.

---

## 7. Durbin–Watson Statistic

Some Rietveld environments, including GSAS-II, report a Durbin–Watson statistic or related residual-correlation diagnostic.

This tests whether neighboring residuals are serially correlated.

#### Advantages

- Useful for detecting systematic structure in the residuals.
- Sensitive to peak-shape, background, and calibration problems.
- Complements \(R_{wp}\) and \(\chi^2\), which may not reveal correlated residuals clearly.

#### Pitfalls

- Not a general fit-quality score.
- Depends on point ordering and data correlations.
- May be difficult to interpret for rebinned, smoothed, or heavily processed data.

---

# 8. Software-Specific Nomenclature and Implementation Differences

## 8.1 GSAS and GSAS-II

Commonly reported quantities include:

- \(R_{wp}\)
- \(R_p\)
- \(\chi^2\)
- GOF
- histogram-level residuals
- phase-related crystallographic residuals
- Durbin–Watson statistic

### Important notes

GSAS/GSAS-II can refine multiple histograms simultaneously. Therefore, global \(\chi^2\) may include contributions from several datasets, phases, restraints, constraints, and other penalty terms.

GSAS-II also reports histogram-level residuals, which are often more useful than only considering the global project-wide value.

### Pitfalls

- A global \(\chi^2\) may not represent the quality of any one dataset.
- Histogram-level \(R_{wp}\) values should be inspected separately.
- Restraints and constraints may affect the reported goodness of fit.
- Profile metrics should be interpreted alongside residual plots and physically meaningful parameters.

---

## 8.2 FullProf

Commonly reported quantities include:

- \(R_p\)
- \(R_{wp}\)
- \(R_{exp}\)
- Chi2
- Bragg R-factor
- RF-factor

### Important notes

FullProf commonly reports **Chi2** as:

\[
\chi^2 = \left(\frac{R_{wp}}{R_{exp}}\right)^2
\]

FullProf also reports phase-specific Bragg and structure-factor metrics, which are important for assessing structural agreement.

### Pitfalls

- Chi2 is typically the squared goodness-of-fit quantity, not the square root.
- FullProf supports different weighting and refinement modes, so values should not be compared without checking the refinement settings.
- Phase-specific metrics are often more informative than global profile metrics for multiphase refinements.

---

## 8.3 TOPAS

Commonly reported quantities include:

- \(R_p\)
- \(R_{wp}\)
- \(R_{exp}\)
- GOF
- background-corrected or primed residuals, such as \(R_p'\), \(R_{wp}'\), and \(R_{exp}'\)

### Important notes

TOPAS distinguishes between standard profile residuals and background-corrected residuals. This can be very important when the background is large.

### Pitfalls

- Background-corrected and non-background-corrected R-factors should not be mixed.
- TOPAS GOF may need to be checked carefully to determine whether it is reporting \(R_{wp}/R_{exp}\) or a squared convention in a specific context.
- Excellent agreement in a global profile metric can still hide phase-specific or structural problems.

---

## 8.4 JANA2006 / Jana2020

Commonly reported quantities may include:

- profile residuals
- \(R_p\)
- \(R_{wp}\)
- GOF
- crystallographic \(R\)-factors
- dataset-specific residuals

### Important notes

Jana is a general crystallographic refinement package that can handle powder, single-crystal, modulated structures, magnetic structures, and combined refinements. Therefore, the meaning of a reported residual depends strongly on the dataset and refinement mode.

### Pitfalls

- Be clear whether the reported metric refers to powder profile agreement, integrated intensities, single-crystal data, or a combined refinement target.
- In combined refinements, a single global metric may hide poor agreement in one data component.
- Powder profile residuals and crystallographic residuals should be interpreted separately.

---

## 8.5 MAUD

Commonly reported quantities include:

- \(R_{wp}\)
- \(R_{exp}\)
- GOF
- phase-related residuals
- texture and microstructure-related fit metrics depending on workflow

### Important notes

MAUD is often used for combined analysis of diffraction, texture, microstructure, residual stress, and related data. Global metrics may therefore combine heterogeneous information.

### Pitfalls

- Global fit indicators may mix contributions from different measurement types.
- Texture, strain, and microstructure models can improve profile agreement while introducing parameter correlations.
- Phase-specific and dataset-specific residuals should be inspected separately.

---

## 8.6 Other Packages: RIETAN, DBWS, BGMN, HighScore Plus, etc.

Most Rietveld packages report some combination of:

- \(R_p\)
- \(R_{wp}\)
- \(R_{exp}\)
- GOF or \(\chi^2\)
- Bragg R-factors
- structure-factor R-factors

### Important notes

The broad concepts are similar across packages, but implementation details differ.

### Common differences

Packages may differ in:

- whether GOF is reported as \(R_{wp}/R_{exp}\) or \((R_{wp}/R_{exp})^2\)
- how weights are defined
- how zero-count or low-count points are handled
- whether excluded regions are included in metric calculations
- how background points are treated
- how constraints and restraints contribute to \(\chi^2\)
- how multiple datasets are combined
- how phase-specific residuals are computed
- whether residuals are reported as fractions or percentages

---

# 9. Common Interpretation Pitfalls

## 9.1 Low \(R_{wp}\) Does Not Guarantee a Correct Structure

A low \(R_{wp}\) can result from:

- high background
- noisy data
- overestimated uncertainties
- weak Bragg peaks
- excessive parameterization
- an over-flexible background
- broad peaks that reduce visible mismatch

## 9.2 High \(R_{wp}\) Does Not Necessarily Mean a Bad Structure

A high \(R_{wp}\) can result from:

- very high counting statistics
- small systematic errors
- imperfect peak-shape model
- detector artifacts
- minor unmodeled impurity peaks
- incorrect uncertainty estimates

High-quality data can make tiny model imperfections statistically significant.

## 9.3 \(\chi^2 \approx 1\) Is Not Proof of Correctness

Reduced \(\chi^2\) near 1 only means that the weighted residual is consistent with the assigned uncertainties under the model assumptions.

It does not prove that:

- the phase model is correct
- the atomic coordinates are correct
- the background is physically meaningful
- microstructure parameters are unique
- impurity phases are absent
- systematic errors are negligible

## 9.4 Background Can Dominate Profile Metrics

Because \(R_{wp}\) is normalized by the total observed intensity, a high background can make profile residuals appear better than they really are.

This is especially important for:

- high-pressure diffraction
- diamond-anvil-cell data
- Paris–Edinburgh cell data
- in situ experiments
- neutron data with strong sample-environment scattering
- amorphous or poorly crystalline samples

In such cases, background-corrected metrics, residual plots, and phase-specific Bragg metrics may be more informative.

## 9.5 Metrics Are Not Always Comparable Between Packages

Even when packages use the same symbols, they may differ in implementation.

For example:

- One package’s `GOF` may equal another package’s `sqrt(Chi2)`.
- One package may report \(R_{wp}\) as a percentage, another as a fraction.
- One package may include restraints in \(\chi^2\), another may report profile-only values.
- One package may report background-corrected residuals, another may not.
- Multipattern refinements may use different weighting of histograms.

---

# 10. Recommendations for Reporting Rietveld Quality

For a publication, report, or internal comparison, it is usually best to include:

- \(R_p\)
- \(R_{wp}\)
- \(R_{exp}\)
- \(\chi^2\) or GOF, with definition
- whether values are percentages or fractions
- phase-specific \(R_{Bragg}\) and/or \(R_F\)
- number of observations
- number of refined parameters
- weighting scheme
- excluded regions
- background treatment
- restraints or constraints used
- whether multiple histograms/datasets were refined together
- observed/calculated/difference plot
- physically meaningful checks on refined parameters

For complex samples, also inspect:

- residual curves
- unmodeled peaks
- peak asymmetry
- background correlations
- phase fractions
- preferred orientation parameters
- strain/size broadening parameters
- displacement parameters
- bond distances and angles
- parameter uncertainties and correlations

---

# 11. Practical Rule of Thumb

Use \(R_{wp}\) and \(\chi^2\) to monitor whether a refinement is improving.

Use \(R_{Bragg}\), \(R_F\), chemical reasonableness, parameter uncertainties, and residual plots to judge whether the structural model is credible.

Do not use any single metric as proof of refinement quality.

The best Rietveld assessment is a combination of:

1. statistically meaningful profile agreement,
2. chemically and physically sensible parameters,
3. absence of systematic residuals,
4. stable refinement behavior,
5. appropriate treatment of background, microstructure, and sample environment,
6. transparent reporting of how metrics were calculated.