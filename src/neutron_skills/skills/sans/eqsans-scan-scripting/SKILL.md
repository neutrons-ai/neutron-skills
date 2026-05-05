---
name: eqsans-scan-scripting
description: Write Python scan scripts for the EQSANS (Extended Q-range Small-Angle Neutron Scattering) instrument at the SNS. Use when the user needs to acquire SANS data on EQSANS, configure sample environments, set wavelength bands, or drive motors for a run sequence.
version: 2
review:
  status: pending
  reviewer: null
  reviewed_on: null
  basis: []
  notes: >
    v2: restructured to required skill anatomy (Overview / When to Use /
    Process / Rationalizations / Red Flags / Verification). Existing scripting
    guidance retained and reorganized.
  approved_commit: null
allowed-tools: Read Write Bash(python:*)
metadata:
  instruments: [EQSANS, SNS]
  techniques: [SANS, small-angle-neutron-scattering]
  tags: [scan, script, acquisition]
---

# EQSANS Scan Scripting

## Overview

Use this skill when writing a scan script to acquire SANS data on **EQSANS**
at the Spallation Neutron Source (SNS).

## When to Use

Use this skill when:

- You need to write or review Python scan scripts for EQSANS acquisition.
- The script must control sample environment setpoints and run sequencing.
- You need consistent metadata/logging for downstream reduction workflows.

Do not use this skill when:

- You are reducing data or fitting models.
- You need generic neutron-scattering planning without instrument scripting.

## Process

1. Choose the framing mode and wavelength band before finalizing aperture and
  detector configuration.
2. Define the scan loops (sample, temperature/field/other conditions, count
  duration) and include settling waits for each controlled parameter.
3. Ensure each run logs the minimum metadata required by reduction pipelines.
4. Pre-plan background/transmission runs in the same configuration family.
5. Validate safety and ramp-rate constraints before launch.

### Key reminders

- EQSANS supports **framing modes** (choppers) that set the accessible
  wavelength band. Pick the frame before setting the sample aperture.
- Wait for the sample environment (temperature, field) to reach its setpoint
  *and* settle before starting the count.
- Always log `run_number`, `title`, `sample`, and `configuration` so the
  reduction pipeline can pick them up.

### Script skeleton

```python
# Pseudocode — substitute your facility's control system calls.
def run_scan(samples, temperatures, count_seconds):
    for sample in samples:
        mount(sample)
        for t in temperatures:
            set_temperature(t)
            wait_settled(tolerance=0.1, timeout=600)
            title = f"{sample.name} @ {t}K"
            start_run(title=title)
            count(seconds=count_seconds)
            end_run()
```

### Pre-launch checklist

1. Frame / wavelength band selected
2. Sample aperture and detector distance recorded
3. Background / transmission runs scheduled
4. Sample environment ramp rates within safe limits

## Rationalizations

| Excuse | Rebuttal |
|--------|----------|
| "I can set the frame mode later after writing the script." | Frame/chopper choice affects usable wavelength and therefore what the whole scan sequence means scientifically. It should be fixed up front. |
| "Setpoint reached is good enough; no need to wait for settling." | Transient sample-environment conditions can invalidate run comparability; wait for settled conditions before counting. |
| "Logging fields are optional because I know the run context." | Missing metadata breaks automated reduction and future traceability for everyone else. |

## Red Flags

- Run titles/configuration fields are missing or inconsistent across the scan.
- Counting starts immediately after setpoint commands without a settle check.
- Background/transmission runs are absent for configurations that require them.
- Frame mode and wavelength-band assumptions are not explicit in the script.

## Verification

- [ ] Frame mode and wavelength band are explicitly selected before counting.
- [ ] All controlled sample-environment variables include settle waits.
- [ ] Run metadata includes `run_number`, `title`, `sample`, and
      `configuration`.
- [ ] Background and transmission runs are planned/scheduled where required.
- [ ] Ramp-rate and safety constraints are satisfied for the full sequence.
