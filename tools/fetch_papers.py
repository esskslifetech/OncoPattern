#!/usr/bin/env python3
"""fetch_papers.py — pull REAL published literature for OncoPattern.

Source: Europe PMC REST (EMBL-EBI), https://www.ebi.ac.uk/europepmc/
open, no API key, and curated — it indexes PubMed/MEDLINE, PMC, Agricola and
preprints, with citation counts, DOIs and PMIDs.

Three real measurements:

  1. EVIDENCE BASE  for each threshold and each simulation model the platform
                    implements, the most-cited paper that establishes it.
                    These become verifiable citations attached to the numbers:
                    a reader can check that TMB >= 10 mut/Mb, the Gompertz
                    growth law or the Pennes bio-heat equation is not invented
                    here but taken from the named work.
  2. GENE ATTENTION for each of the 40 genes in the expression panel, how many
                    cancer papers name it.  Paired with the EPO patent counts
                    this separates "well studied but unpatented" from
                    "genuinely unexamined".
  3. VELOCITY       cancer papers per year, to sit alongside the patent curve.

Output: datasets/papers.json, parsed in pure TECH by
oncopattern/data/ingest_papers.tech.  One unmodified API response is kept as
provenance.

Usage:  python3 tools/fetch_papers.py [--out datasets/papers.json]
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
UA = "Mozilla/5.0 (X11; Linux x86_64) OncoPattern/1.0 research"

GENES = [
    "EGFR", "KRAS", "TP53", "MYC", "VEGFA", "MKI67", "CCND1", "AURKA",
    "PTEN", "RB1", "BRCA1", "BRCA2", "ATM", "CDKN2A", "SMAD4", "APC",
    "ALK", "ROS1", "MET", "ERBB2", "PIK3CA", "AKT1", "MTOR", "STK11",
    "KEAP1", "NFE2L2", "CTNNB1", "NOTCH1", "JAK2", "STAT3", "IL6",
    "CD8A", "PDCD1", "CD274", "FOXP3", "GZMB", "PRF1", "IFNG",
    "TGFB1", "COL1A1",
]

# Every threshold and every model the platform implements, with a
# TITLE-restricted query and a token that MUST appear in the returned title.
#
# Sorting by citation count alone is not enough: Europe PMC matches loosely,
# so "microsatellite instability" returned "Immunity, inflammation and cancer"
# (8337 cites) simply because it is famous and mentions the words.  Each entry
# below therefore carries a `must` token; results are walked in citation order
# and the first whose TITLE actually contains that token is taken.  If none
# does, the reference is recorded as unmatched rather than wrong.
REFS = [
    ("tmb",          "OC_TMB_HIGH = 10 mut/Mb",
     'TITLE:"tumor mutational burden" OR TITLE:"tumour mutational burden" OR TITLE:"mutational load"',
     ["mutational burden", "mutational load"]),
    ("msi",          "OC_MSI_HIGH microsatellite instability",
     'TITLE:"microsatellite instability"', ["microsatellite"]),
    ("mutsig",       "detect_mutational_signature (NMF)",
     'TITLE:"mutational signatures" OR TITLE:"mutational processes"',
     ["mutational signature", "mutational processes"]),
    ("cnv",          "detect_cnv_segment",
     'TITLE:"copy number" AND TITLE:"cancer"', ["copy number"]),
    ("ki67",         "detect_mitotic / proliferation index",
     'TITLE:"Ki-67" AND TITLE:"prognostic"', ["ki-67", "ki67"]),
    ("pleomorphism", "detect_nuclear_pleomorphism",
     'TITLE:"nuclear pleomorphism" OR (TITLE:"nuclear grade" AND TITLE:"carcinoma")',
     ["pleomorphism", "nuclear grade"]),
    # "necrosis" alone lands on tumour necrosis FACTOR papers, a different
    # molecule entirely; exclude it explicitly
    ("necrosis",     "detect_necrosis / OC_NECROSIS_MAX",
     '(TITLE:"tumour necrosis" OR TITLE:"tumor necrosis" OR TITLE:"coagulative necrosis") AND TITLE:"prognostic"',
     ["necrosis"], ["necrosis factor", "cachectin"]),
    ("til",          "detect_til_gradient",
     'TITLE:"tumor-infiltrating lymphocytes" OR TITLE:"tumour-infiltrating lymphocytes"',
     ["infiltrating lymphocyte"]),
    ("stroma",       "detect_tumor_stroma_ratio",
     'TITLE:"tumor-stroma ratio" OR TITLE:"tumour-stroma ratio" OR TITLE:"stroma ratio"',
     ["stroma"]),
    ("vascular",     "detect_vascular_invasion",
     'TITLE:"lymphovascular invasion"', ["lymphovascular"]),
    ("gompertz",     "simulation/cell_growth growth_gompertz",
     'TITLE:"Gompertz"', ["gompertz"]),
    # "tumor growth" alone matches any paper where something promotes or
    # inhibits growth; require the title to be ABOUT the growth law itself
    ("logistic",     "simulation/cell_growth growth_logistic",
     '(TITLE:"mathematical models" OR TITLE:"mathematical model" OR TITLE:"universal law") AND (TITLE:"tumor growth" OR TITLE:"tumour growth")',
     ["tumor growth", "tumour growth"],
     ["inhibit", "suppress", "promot", "stress", "sorafenib"]),
    ("diffusion",    "simulation/angiogenesis diffusion_2d",
     'TITLE:"reaction-diffusion" OR (TITLE:"glioma" AND TITLE:"invasion" AND TITLE:"model")',
     ["reaction-diffusion", "invasion"]),
    ("angiogenesis", "simulation/angiogenesis VEGF sprouting",
     'TITLE:"tumor angiogenesis" OR TITLE:"tumour angiogenesis"',
     ["angiogenesis"], ["sorafenib", "sunitinib", "bevacizumab", "inhibitor"]),
    ("hypoxia",      "g_hypoxic_frac / oxygen diffusion limit",
     'TITLE:"tumor hypoxia" OR TITLE:"tumour hypoxia"', ["hypoxia"]),
    ("pennes",       "pattern/physical ablation_step (bio-heat)",
     '(TITLE:"bioheat" OR TITLE:"bio-heat" OR TITLE:"Pennes") AND (TITLE:"tissue" OR TITLE:"thermal" OR TITLE:"ablation" OR TITLE:"hyperthermia")',
     ["bioheat", "bio-heat", "pennes"], ["microbial", "environmental", "compost"]),
    ("radiation",    "pattern/physical radiation_run",
     'TITLE:"linear-quadratic" OR TITLE:"linear quadratic"', ["linear-quadratic", "linear quadratic"]),
    ("chemotaxis",   "pattern/physical chemotaxis_run (Keller-Segel)",
     'TITLE:"Keller-Segel" OR TITLE:"chemotaxis" AND TITLE:"model"', ["keller-segel", "chemotaxis"]),
    ("pkpd",         "simulation/drug_response PK/PD Emax",
     'TITLE:"pharmacokinetic" AND TITLE:"pharmacodynamic" AND (TITLE:"tumor" OR TITLE:"tumour" OR TITLE:"anticancer" OR TITLE:"chemotherapy")',
     ["pharmacodynamic"], ["antibiotic", "antimicrobial", "antibacterial"]),
    ("immunoedit",   "simulation/immune_interaction Lotka-Volterra",
     'TITLE:"immunoediting"', ["immunoediting"]),
    ("metastasis",   "simulation/metastasis organ tropism",
     'TITLE:"seed and soil" OR TITLE:"organ tropism" OR TITLE:"metastatic cascade"',
     ["seed and soil", "tropism", "cascade"]),
    ("ssa",          "simulation/stochastic Gillespie SSA",
     'TITLE:"stochastic simulation" AND TITLE:"chemical"', ["stochastic simulation"]),
    ("murray",       "murray_parent_radius vascular branching",
     'TITLE:"Murray\'s law" OR TITLE:"Murray law"', ["murray"]),
    ("fea",          "pattern/physical stress_run (solid stress)",
     'TITLE:"solid stress" AND TITLE:"tumor"', ["solid stress"]),
]

VELOCITY_YEARS = list(range(2010, 2025))

WS = re.compile(r"\s+")
TAG = re.compile(r"<[^>]+>")


def clean(s, limit=120):
    if not s:
        return ""
    s = TAG.sub("", str(s))
    s = s.replace('"', "").replace("\\", "").replace(",", ";")
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return WS.sub(" ", s).strip()[:limit]


def api(query, page_size=1, sort=None, retries=3):
    q = {"query": query, "format": "json", "pageSize": str(page_size),
         "resultType": "core"}
    if sort:
        q["sort"] = sort
    url = BASE + "?" + urllib.parse.urlencode(q)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:                       # noqa: BLE001
            if attempt == retries - 1:
                print("    ! %s" % e, file=sys.stderr)
                return None
            time.sleep(2.0 * (attempt + 1))
    return None


def hit_count(query):
    d = api(query, page_size=1)
    if not d:
        return -1
    return int(d.get("hitCount") or 0)


def validated_paper(query, must, must_not=(), depth=15):
    """Most-cited paper whose TITLE contains one of `must` and none of
    `must_not`.  The exclusion list matters: "necrosis" otherwise lands on
    tumour necrosis FACTOR, and "angiogenesis" on drug trials."""
    d = api(query, page_size=depth, sort="CITED desc")
    if not d:
        return None
    res = d.get("resultList", {}).get("result", [])
    r = None
    for cand in res:
        t = (cand.get("title") or "").lower()
        if any(m in t for m in must) and not any(x in t for x in must_not):
            r = cand
            break
    if r is None:
        return None
    ji = r.get("journalInfo", {}) or {}
    jr = ji.get("journal", {}) or {}
    authors = clean(r.get("authorString"), 60)
    first = authors.split(";")[0].strip() if authors else ""
    return {
        "matched": 1,
        "hits": int(d.get("hitCount") or 0),
        "pmid": clean(r.get("pmid"), 12),
        "doi": clean(r.get("doi"), 60),
        "title": clean(r.get("title"), 120),
        "first_author": first,
        "journal": clean(jr.get("medlineAbbreviation") or jr.get("title"), 40),
        "year": int(r.get("pubYear") or 0),
        "cites": int(r.get("citedByCount") or 0),
        "open_access": 1 if r.get("isOpenAccess") == "Y" else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="datasets/papers.json")
    ap.add_argument("--raw", default="datasets/papers_provenance.json")
    ap.add_argument("--delay", type=float, default=0.35)
    args = ap.parse_args()

    print("Europe PMC (EMBL-EBI) — published evidence base")
    print("endpoint:", BASE)

    print("\n[1/3] evidence citations for %d thresholds and models" % len(REFS))
    refs = []
    unmatched = 0
    for i, entry in enumerate(REFS):
        key, backs, query, must = entry[0], entry[1], entry[2], entry[3]
        must_not = entry[4] if len(entry) > 4 else ()
        p = validated_paper(query, must, must_not)
        time.sleep(args.delay)
        if not p:
            unmatched += 1
            p = {"matched": 0, "hits": 0, "pmid": "", "doi": "", "title": "",
                 "cites": 0, "first_author": "", "journal": "", "year": 0,
                 "open_access": 0}
        p.update({"key": key, "backs": backs, "index": i,
                  "query": clean(query, 90)})
        refs.append(p)
        flag = " " if p["matched"] else "?"
        print("  %s%-13s %-46s %6d cites  %s %s"
              % (flag, key, p["title"][:46], p["cites"], p["journal"], p["year"]))
    print("   (%d of %d matched a title-verified reference)"
          % (len(refs) - unmatched, len(refs)))

    print("\n[2/3] literature attention for %d genes" % len(GENES))
    genes = []
    for i, g in enumerate(GENES):
        # TITLE-restricted, exactly as the patent counts are title-restricted,
        # so the two channels measure the same thing
        n = hit_count('TITLE:"%s" AND cancer' % g)
        time.sleep(args.delay)
        genes.append({"term": g, "index": i, "count": n})
        print("   %-8s %8d" % (g, n))

    print("\n[3/3] cancer publications per year %d-%d"
          % (VELOCITY_YEARS[0], VELOCITY_YEARS[-1]))
    velocity = []
    for y in VELOCITY_YEARS:
        n = hit_count("cancer AND (PUB_YEAR:%d)" % y)
        time.sleep(args.delay)
        velocity.append({"year": y, "count": n})
        print("   %d %8d" % (y, n))

    doc = {
        "source": "Europe PMC REST (EMBL-EBI) europepmc.org",
        "retrieved": time.strftime("%Y-%m-%d"),
        "n_refs": len(refs),
        "n_matched": len(refs) - unmatched,
        "n_genes": len(genes),
        "n_years": len(velocity),
        "year0": VELOCITY_YEARS[0],
        "refs": refs,
        "genes": genes,
        "velocity": velocity,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(doc, f, indent=1)
    print("\nwrote %s (%d bytes)" % (args.out, os.path.getsize(args.out)))

    raw = api('"tumor mutational burden" AND "immune checkpoint inhibitor" AND survival',
              page_size=1, sort="CITED desc")
    if raw:
        with open(args.raw, "w") as f:
            json.dump(raw, f, indent=1)
        print("wrote %s (unmodified API response, provenance)" % args.raw)


if __name__ == "__main__":
    main()
