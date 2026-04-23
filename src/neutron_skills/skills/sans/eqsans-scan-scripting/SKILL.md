---
name: eqsans-scan-scripting
description: Write Python scan scripts for the EQSANS (Extended Q-range Small-Angle Neutron Scattering) instrument at the SNS. Use when the user needs to acquire SANS data on EQSANS, configure sample environments, set wavelength bands, or drive motors for a run sequence.
allowed-tools: Read Write Bash(python:*)
metadata:
  instruments: [EQSANS, SNS]
  techniques: [SANS, small-angle-neutron-scattering]
  tags: [scan, script, acquisition]
---

# EQSANS Scan Scripting

Use this skill when writing a scan script to acquire SANS data on **EQSANS**
at the Spallation Neutron Source (SNS).

## Key reminders

- EQSANS supports **framing modes** (choppers) that set the accessible
  wavelength band. Pick the frame before setting the sample aperture.
- Wait for the sample environment (temperature, field) to reach its setpoint
  *and* settle before starting the count.
- Always log `run_number`, `title`, `sample`, and `configuration` so the
  reduction pipeline can pick them up.

## Script skeleton

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

## Checklist before launching

1. Frame / wavelength band selected
2. Sample aperture and detector distance recorded
3. Background / transmission runs scheduled
4. Sample environment ramp rates within safe limits
