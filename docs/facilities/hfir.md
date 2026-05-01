# High Flux Isotope Reactor (HFIR) — Data Model

This document records stable facts about HFIR data that skill authors and
contributors should treat as ground truths. Instrument-specific decisions
live in `docs/instruments/`.

---

## Source type

HFIR is a **steady-state** (continuous) neutron source. Unlike the pulsed
SNS, neutrons are produced continuously. This fundamentally changes data
acquisition: there are no discrete pulses and no Time-of-Flight dimension
in the same sense as SNS.

---

## TODO: fill in remaining sections

The following sections should be completed with facility-specific details:

- Raw data format and histogram/counting conventions
- File format and NeXus schema variant used at HFIR
- Metadata and log conventions
- Mantid workspace types used for HFIR data
- Key differences from SNS that affect skill authoring
