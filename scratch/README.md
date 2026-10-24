# scratch — language probes

Throwaway programs written while establishing how TECH actually behaves on this
machine. They are not part of the product and nothing in `oncopattern/` imports
them; they are kept as the evidence behind the "Notes on the toolchain" section
of the main README.

| file | what it established |
|---|---|
| `smoke.tech` | basic execution, `YIELD`, arithmetic |
| `s2.tech` | byte buffers, `strbuf`/`slice`/`len`, that `str + str` yields `0` |
| `s3.tech` | float behaviour, `//// 1` truncation, no scientific-notation literals |
| `s4.tech` | `save`/`load` round-trip, `sha256`, `data<>` records |
| `s5.tech` | `FLOW` ranges and mass-conserving diffusion on a grid |
| `s6.tech` | that `print()` produces no output on `bootstrap/stage0/vm` |
| `m1.tech` | the `MATCH` + nested-`WHILE` compiler failure (emits a 0-byte object) |
| `linked.tech`, `l.tbc`, `raw.bin` | `techc link` output and packaging inspection |

Run one with:

```bash
cd ../../../TECH && ./bootstrap/stage0/stage0 ../Projects/OncoPattern/scratch/s2.tech /tmp/s2.tbc && ./bootstrap/stage0/vm /tmp/s2.tbc
```
