# Security policy

## What this repository is

OncoPattern is a **demonstration platform**, not a medical device. It has no
network listeners, no privileged operations, no authentication and no user
accounts. It reads files from `ocdata/`, writes files to `ocout/`, and runs
entirely inside the TECH virtual machine.

The only code that talks to the outside world is in `tools/` and runs only when
you invoke it by hand:

| Tool | Endpoint |
|---|---|
| `tools/fetch_patents.py` | European Patent Office Linked Open Data SPARQL endpoint |
| `tools/fetch_papers.py` | Europe PMC REST search |
| `tools/bmp2png.py` | none — local conversion |

None of these are called by the pipeline, the certificates, or `make test`.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository
(**Security → Report a vulnerability**). Please do not open a public issue for
anything you believe is exploitable.

Useful in a report:

- the smallest input file or `.tech` program that triggers the behaviour;
- what you expected and what happened;
- whether the defect is in `oncopattern/**` (this repository) or in the TECH
  toolchain it runs on — toolchain defects belong upstream at
  [esskslifetech/TECH](https://github.com/esskslifetech/TECH).

## Scope

In scope: malformed-input handling in the parsers under `oncopattern/data/`
(out-of-bounds reads, unbounded allocation, crashes on hostile CSV/VCF/JSON/PGM),
and path handling in the export and journaling layers.

Out of scope: the TECH compiler and VM themselves, the digest of synthetic
fixtures under `datasets/`, and anything that depends on treating the
simulation output as clinical guidance — which it is not.

## Supported versions

The repository is developed on `main`; fixes land there. There are no
maintained release branches.
