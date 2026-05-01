# Spallation Neutron Source (SNS) — Data Model

This document records stable facts about SNS data that skill authors and
contributors should treat as ground truths. Instrument-specific decisions
live in `docs/instruments/`.

---

## Source type

The SNS is a **pulsed** neutron source. Neutrons are produced in discrete
pulses at a fixed repetition rate. This is the defining characteristic that
shapes every aspect of SNS data acquisition and reduction.

---

## Raw data: event mode

SNS instruments record data in **full event mode**. The raw data are lists
of individual neutron detection events. Each event carries three attributes:

| Attribute | Description |
|---|---|
| Pulse ID | Which pulse generated the neutron; combined with the facility clock this gives an absolute wall-clock timestamp. |
| Pixel ID | Which detector pixel registered the event. |
| Time-of-Flight (TOF) | Time offset in microseconds between neutron generation in a specific pulse and detection of that neutron at the pixel. |

TOF can be converted to the physical quantity **neutron wavelength** (λ) via:

$$\lambda = \frac{h \cdot \text{TOF}}{m_n \cdot L}$$

where $h$ is Planck's constant, $m_n$ is the neutron mass, and $L$ is the
total flight path length from source to detector.

---

## File format

- **Schema**: standardised NeXus/HDF5
- **Extension**: `.nxs.h5`
- **Access**: files on disk or directly from a live data stream during acquisition

The NeXus schema is standardised across SNS instruments, though
instrument-specific metadata fields vary.

---

## Metadata and PV logs

Each file contains standardised metadata including **time-series process
variable (PV) logs** — records of experimental conditions (temperature,
magnetic field, sample environment states, etc.) sampled against the
facility wall-clock timeline. These logs share the same time axis as the
pulse timestamps, enabling event filtering by experimental condition.

---

## Mantid representation

Mantid is the primary framework for SNS data processing. The key workspace
type for SNS event data is:

- **`EventWorkspace`**: holds the full event list (pulse ID, pixel ID, TOF)
  plus a description of the instrument geometry and metadata. Mantid provides
  many algorithms and methods that operate on `EventWorkspace` objects,
  including TOF-to-wavelength conversion, event filtering by PV log values,
  rebinning, and focussing.

Other relevant Mantid workspace types (used after rebinning or conversion):

- **`Workspace2D`**: binned histogram data; produced when events are
  integrated or rebinned.
- **`MDEventWorkspace`** / **`MDHistoWorkspace`**: multi-dimensional data;
  used for single-crystal or advanced analyses.

---

## Pixel grouping and masking

SNS event-mode data enables flexible combination of detector pixels into
spectra before or during reduction. This is called **pixel grouping** and it
directly affects both **resolution** and **counting statistics** — a core
scientific tradeoff that users must consider.

Grouping is defined by a grouping scheme: a map from pixel IDs to output
spectrum indices. Multiple schemes may be applied to the same dataset.

Two types of masking work alongside pixel grouping:

| Mask type | Scope | Description |
|---|---|---|
| `pixelmask` | Whole pixels | Excludes entire pixels from reduction regardless of their TOF content. Used for known bad detectors or detector regions. |
| `binmask` | Data ranges within pixels | Excludes specific ranges of the measured quantity within pixels. Can be specified in any supported unit: **TOF** (µs), **wavelength** (Å), **Q** (Å⁻¹), or **d-spacing** (Å). This is a key TOF capability: the same pixel may contribute valid data in some ranges and invalid data in others. |

The combination of grouping scheme, pixelmasks, and binmasks defines the
effective detector coverage for a reduction run. Changes to any of these
affect the resulting resolution and signal-to-noise.

---

## Instrument-specific docs

Each SNS instrument that has skills in this repository has a corresponding
decision record in `docs/instruments/`. Those files reference back here for
the shared data model and document only instrument-specific conventions.
