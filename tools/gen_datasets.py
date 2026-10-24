#!/usr/bin/env python3
"""Deterministic synthetic dataset generator for OncoPattern.

Ground truth is fixed by construction so the .tech test-suite can assert
exact counts (see oncopattern/test/*.tech).  Pure stdlib, seeded LCG so the
output is byte-identical on every machine.
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datasets")
OUT = os.path.normpath(OUT)
os.makedirs(OUT, exist_ok=True)


class LCG:
    """Same LCG the .tech stochastic module uses (Numerical Recipes)."""

    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFF

    def next(self):
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return self.s

    def unit(self):
        return self.next() / 4294967296.0

    def rint(self, lo, hi):
        return lo + self.next() % (hi - lo)


BASES = "ACGT"

# ---------------------------------------------------------------- clinical
def gen_clinical():
    rows = [
        "patient_id,cancer_type,stage,age,tumor_volume_cm3,treatment,months_followup",
        "P001,LUAD,3,64,42.5,chemo_immuno,18",
        "P002,BRCA,2,51,18.2,hormone,24",
        "P003,COAD,4,72,88.9,chemo,9",
        "P004,LUAD,1,58,6.4,surgery,36",
        "P005,GBM,4,49,61.3,radio_chemo,11",
        "P006,BRCA,3,66,33.1,chemo_immuno,21",
    ]
    with open(f"{OUT}/clinical.csv", "w") as f:
        f.write("\n".join(rows) + "\n")
    return len(rows) - 1


# --------------------------------------------------------------------- VCF
def gen_vcf(name, seed, n_variants, hotspot_center, hotspot_n, n_bad, tmb_extra=0):
    """A VCF with a known SNV hotspot cluster and a known number of bad rows."""
    r = LCG(seed)
    lines = [
        "##fileformat=VCFv4.2",
        "##source=OncoPattern-synthetic",
        "##reference=GRCh38",
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
    ]
    recs = []
    # background variants spread over chr1..chr22
    for _ in range(n_variants - hotspot_n - tmb_extra):
        c = r.rint(1, 23)
        p = r.rint(10000, 2490000)
        recs.append((c, p))
    # hotspot cluster: hotspot_n variants inside a 5 kb window on chr7
    for _ in range(hotspot_n):
        p = hotspot_center + r.rint(0, 5000)
        recs.append((7, p))
    for _ in range(tmb_extra):
        recs.append((3, r.rint(10000, 2490000)))
    recs.sort()

    for (c, p) in recs:
        ri = r.rint(0, 4)
        ai = (ri + 1 + r.rint(0, 3)) % 4
        qual = 20.0 + r.unit() * 80.0
        lines.append(
            f"chr{c}\t{p}\t.\t{BASES[ri]}\t{BASES[ai]}\t{qual:.1f}\tPASS\tDP={r.rint(20,200)}"
        )
    # deliberately invalid rows -> must be quarantined, never silently dropped
    bad = [
        "chr9\t-500\t.\tA\tT\t55.0\tPASS\tDP=40",          # negative position
        "chr5\t120000\t.\tA\tT\t-3.0\tPASS\tDP=40",         # negative quality
        "chr99\t500000\t.\tG\tC\t44.0\tPASS\tDP=30",        # chromosome out of range
    ][:n_bad]
    lines.extend(bad)
    with open(f"{OUT}/{name}", "w") as f:
        f.write("\n".join(lines) + "\n")
    return len(recs), len(bad)


# ------------------------------------------------------------- expression
def gen_expression():
    """40 genes x 12 samples log2(FPKM+1); samples 6..11 are the tumour group
    with 8 deliberately up-regulated genes (rows 0..7)."""
    r = LCG(20260823)
    genes = [
        "EGFR", "KRAS", "TP53", "MYC", "VEGFA", "MKI67", "CCND1", "AURKA",
        "PTEN", "RB1", "BRCA1", "BRCA2", "ATM", "CDKN2A", "SMAD4", "APC",
        "ALK", "ROS1", "MET", "ERBB2", "PIK3CA", "AKT1", "MTOR", "STK11",
        "KEAP1", "NFE2L2", "CTNNB1", "NOTCH1", "JAK2", "STAT3", "IL6",
        "CD8A", "PDCD1", "CD274", "FOXP3", "GZMB", "PRF1", "IFNG", "TGFB1",
        "COL1A1",
    ]
    hdr = "gene," + ",".join([f"N{i+1}" for i in range(6)] + [f"T{i+1}" for i in range(6)])
    rows = [hdr]
    for gi, g in enumerate(genes):
        vals = []
        for s in range(12):
            base = 3.0 + (gi % 5) * 0.7
            if s >= 6 and gi < 8:
                base += 4.2                      # tumour up-regulation
            if s >= 6 and 31 <= gi <= 37:
                base -= 1.6                      # immune exhaustion signature
            vals.append(max(0.0, base + (r.unit() - 0.5) * 0.6))
        rows.append(g + "," + ",".join(f"{v:.3f}" for v in vals))
    with open(f"{OUT}/expression.csv", "w") as f:
        f.write("\n".join(rows) + "\n")
    return len(genes), 12


# ---------------------------------------------------------------- pathway
def gen_pathway():
    """Organ-topology graph for metastasis routing (node 0 = primary lung)."""
    organs = ["lung", "lymph_node", "liver", "bone", "brain", "adrenal", "pleura"]
    # edges: from, to, weight = 1/(flow * survival)  (lower = easier route)
    edges = [
        (0, 1, 2), (0, 6, 3), (1, 2, 4), (1, 3, 5), (1, 5, 6),
        (2, 3, 7), (0, 4, 12), (1, 4, 9), (6, 2, 8), (3, 4, 10),
    ]
    lines = ['{', '  "nodes": [']
    lines += ['    {"id": %d, "name": "%s"}%s' % (i, n, "," if i < len(organs) - 1 else "")
              for i, n in enumerate(organs)]
    lines += ['  ],', '  "edges": [']
    lines += ['    [%d, %d, %d]%s' % (a, b, w, "," if k < len(edges) - 1 else "")
              for k, (a, b, w) in enumerate(edges)]
    lines += ['  ]', '}']
    with open(f"{OUT}/pathway.json", "w") as f:
        f.write("\n".join(lines) + "\n")
    return len(organs), len(edges)


# ------------------------------------------------------------------ image
def gen_pgm(name="histology.pgm", W=96, H=96, seed=777):
    """ASCII PGM (P2) pathology field.

    Construction (the ground truth for test_pattern.tech):
      background stroma  ~  60
      tumour sheet       ~ 150  (left 2/3)
      nuclei             ~ 230  (24 round blobs, radius 2..4)
      necrosis core      ~  20  (one filled disc, radius 11, centre (68,30))
    """
    r = LCG(seed)
    px = [[60 for _ in range(W)] for _ in range(H)]
    for y in range(H):
        for x in range(W):
            v = 60 + int(r.unit() * 8)
            if x < (W * 2) // 3:
                v = 150 + int(r.unit() * 10)
            px[y][x] = v
    # necrosis disc
    ncx, ncy, nr = 68, 30, 11
    for y in range(H):
        for x in range(W):
            if (x - ncx) ** 2 + (y - ncy) ** 2 <= nr * nr:
                px[y][x] = 20 + int(r.unit() * 6)
    # nuclei
    nuclei = 0
    for _ in range(24):
        cx, cy = r.rint(6, 60), r.rint(6, H - 6)
        rad = r.rint(2, 5)
        for y in range(cy - rad, cy + rad + 1):
            for x in range(cx - rad, cx + rad + 1):
                if 0 <= x < W and 0 <= y < H and (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                    px[y][x] = 230 + int(r.unit() * 20)
        nuclei += 1
    body = "\n".join(" ".join(str(v) for v in row) for row in px)
    with open(f"{OUT}/{name}", "w") as f:
        f.write(f"P2\n# OncoPattern synthetic pathology field\n{W} {H}\n255\n{body}\n")
    return W, H, nuclei


if __name__ == "__main__":
    npat = gen_clinical()
    n0, b0 = gen_vcf("variants_P001_t0.vcf", 12345, 1000, 55000000, 120, 3)
    n1, b1 = gen_vcf("variants_P001_t1.vcf", 99887, 1000, 55000000, 260, 0, tmb_extra=340)
    ng, ns = gen_expression()
    no, ne = gen_pathway()
    W, H, nn = gen_pgm()
    print(f"clinical.csv          {npat} patients")
    print(f"variants_P001_t0.vcf  {n0} variants + {b0} invalid rows (hotspot 120)")
    print(f"variants_P001_t1.vcf  {n1} variants + {b1} invalid rows (hotspot 260)")
    print(f"expression.csv        {ng} genes x {ns} samples")
    print(f"pathway.json          {no} organs, {ne} edges")
    print(f"histology.pgm         {W}x{H}, {nn} nuclei, necrosis disc r=11 @ (68,30)")
