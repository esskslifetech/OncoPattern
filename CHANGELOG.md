# Changelog

All notable changes to OncoPattern are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Numbers quoted below are measurements from `tools/runtests` and from one
pipeline run (`tools/ocbuild run config/boot.tech oncopattern`) on the machine
that produced the release.

## [1.0.0] — 2026-10-24

First public release. The platform is written entirely in `.tech` and runs on
the [TECH](https://github.com/esskslifetech/TECH) self-hosting toolchain; no
other language appears in the product.

### Added

- **Ingest (P1)** — streaming parsers for VCF, CSV, JSON and Netpbm PGM, with
  schema validation. Malformed records are quarantined with their line, field
  and reason code rather than dropped, and are rendered in the report.
- **Patterns (P2)** — 24 patterns registered through `META @register_pattern`:
  six genomic (SNV hotspot clustering, CNV segmentation, MSI by
  Kolmogorov–Smirnov on inter-variant gaps, mutational signatures by K=2 NMF
  with Lee–Seung updates, TMB per megabase, expression clustering), six
  histological (flood-fill nuclei, nuclear-area CV, mitotic density,
  tumour–stroma ratio, necrosis fraction, radial TIL gradient) and twelve
  physical patterns registered from simulation results, so measured and
  simulated findings are compared by the same engine.
- **Simulation (P3)** — twelve models behind one dispatcher: logistic and
  Gompertz growth (RK4), 2-D diffusion and angiogenesis (coupled
  reaction–diffusion, five-point stencil), Pennes bio-heat ablation, radiation
  with dose–volume histogram, Keller–Segel chemotaxis, mechanical stress (FEA,
  Thomas algorithm), metastasis (Dijkstra over the organ graph), mutation
  cascade (exact dense Markov chain), two-compartment PK/PD, immune
  interaction (Lotka–Volterra) and a Gillespie SSA with a seeded generator.
- **Visualisation (P4)** — 900×660 RGB framebuffer, Bresenham lines, filled and
  outlined circles, a hand-built 5×7 bitmap font, viridis and heat ramps, and
  byte-exact BMP/PPM/SVG export.
- **Exhaustive scan** — 227 signals enumerated across every channel the loaded
  data supports, standardised within channel and ranked by effect size.
- **Novel composites** — nine cross-channel indices (TOI, NDS, RIL, ESI, ICI,
  HIA, MGC, AEA, ODC) that no source dataset defines.
- **Real external data** — `tools/fetch_patents.py` pulls the EPO Linked Open
  Data endpoint and `tools/fetch_papers.py` pulls Europe PMC; the unmodified API
  responses are committed as provenance next to the derived fixtures.
- **Reporting (P5/P6)** — eight-section TXT report, self-contained HTML report
  with the framebuffer embedded, and a two-timepoint comparison engine with
  MATCH / MINOR_CHANGE / MAJOR_CHANGE thresholds and an alerts section.
- **GUI (P7)** — menus, panels, tabs, status bar, widget states, a
  row/column/grid layout engine, modal dialogs, and an event loop that can be
  driven by a scripted queue so the interface is testable.
- **Persistence (P8)** — journaling filesystem with write-ahead logging,
  including a crash drill that proves rollback before commit and redo after it.
- **Certificates** — **453 assertions across nine modules**, all passing, on
  the C machine and on the self-hosted `vm.tech`.
- **Tooling** — `tools/ocbuild` (transient staging, build, run, package),
  `tools/runtests` (every certificate), `tools/check_repo.py` (publishability
  checks that need no toolchain), a `Makefile`, and the dataset generators and
  retrieval tools.

### Known limitations

- Not a medical device. Simulation parameters are order-of-magnitude realistic
  for the named entities and are documented with units; they are software
  defaults, not clinical guidance.
- The patient data is synthetic. Only the patent and literature channels are
  real.
- Performance is interpreter-bound.
- Gene-level attention counts are title-restricted, so they undercount absolute
  attention consistently across patents and papers.

[1.0.0]: https://github.com/esskslifetech/OncoPattern/releases/tag/v1.0.0
