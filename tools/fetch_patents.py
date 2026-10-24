#!/usr/bin/env python3
"""fetch_patents.py — pull REAL patent data for the OncoPattern analysis.

Source: the European Patent Office's official Linked Open Data SPARQL
endpoint, https://data.epo.org/linked-data/query — open, no API key, and
authoritative (it is the EPO's own publication of EP/WO bibliographic data).

Three real measurements are collected:

  1. GENE COVERAGE   for each of the 40 genes in the expression panel, the
                     number of distinct oncology-classified patent
                     publications (IPC A61P35/00, "antineoplastic agents")
                     whose title mentions that gene.
  2. MODALITY CLASSES for the IPC classes that correspond to the platform's
                     own simulation models (radiotherapy -> A61N5/10,
                     RF ablation -> A61B18/14, immunotherapy -> A61K39/395,
                     and so on), the total number of publications.
  3. VELOCITY        publications per year in A61P35/00, which is a genuine
                     oncology innovation curve rather than a synthetic one.

Output: datasets/patents.json, a flat canonical shape parsed in pure TECH by
oncopattern/data/ingest_patents.tech.  One unmodified SPARQL response is kept
alongside it as provenance.

Usage:  python3 tools/fetch_patents.py [--out datasets/patents.json]
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://data.epo.org/linked-data/query"
UA = "Mozilla/5.0 (X11; Linux x86_64) OncoPattern/1.0 research"
IPC = "http://data.epo.org/linked-data/def/ipc/"
ONCO = IPC + "A61P35-00"          # antineoplastic agents

PREFIX = "PREFIX patent: <http://data.epo.org/linked-data/def/patent/>\n"

GENES = [
    "EGFR", "KRAS", "TP53", "MYC", "VEGFA", "MKI67", "CCND1", "AURKA",
    "PTEN", "RB1", "BRCA1", "BRCA2", "ATM", "CDKN2A", "SMAD4", "APC",
    "ALK", "ROS1", "MET", "ERBB2", "PIK3CA", "AKT1", "MTOR", "STK11",
    "KEAP1", "NFE2L2", "CTNNB1", "NOTCH1", "JAK2", "STAT3", "IL6",
    "CD8A", "PDCD1", "CD274", "FOXP3", "GZMB", "PRF1", "IFNG",
    "TGFB1", "COL1A1",
]

# IPC classes chosen to line up with the platform's simulation models
CLASSES = [
    ("A61P35-00", "antineoplastic agents",      "oncology overall"),
    ("A61P35-02", "antineoplastics leukaemia",  "haematological"),
    ("A61N5-10",  "radiotherapy",               "radiation model"),
    ("A61B18-14", "RF electro-surgery",         "thermal_ablation model"),
    ("A61K39-395","antibody immunotherapy",     "immune_interaction model"),
    ("A61K9-51",  "nanoparticle delivery",      "drug_pkpd model"),
    ("C12Q1-6886","nucleic acid cancer assay",  "genomic detectors"),
    ("G01N33-574","tumour marker immunoassay",  "biomarker detectors"),
    ("A61K41-00", "photodynamic ablation",      "ablation adjunct"),
    ("G06T7-00",  "image analysis",             "histology detectors"),
    ("G16H50-20", "clinical decision support",  "reporting layer"),
    ("A61B5-055", "MRI diagnostics",            "spatial imaging"),
]

YEARS = list(range(2010, 2025))

WS = re.compile(r"\s+")


def clean(s, limit=60):
    if not s:
        return ""
    s = str(s).replace('"', "").replace("\\", "").replace(",", ";")
    return WS.sub(" ", s).strip()[:limit]


def sparql(query, retries=4, pause=1.1):
    """Run one SPARQL query, returning parsed JSON bindings (or None)."""
    for attempt in range(retries):
        time.sleep(pause)
        url = (ENDPOINT + "?query=" + urllib.parse.quote(query)
               + "&format=" + urllib.parse.quote("application/sparql-results+json"))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read().decode("utf-8", "replace")
            if not body.lstrip().startswith("{"):
                raise ValueError("non-JSON response (WAF challenge?)")
            return json.loads(body)
        except Exception as e:                       # noqa: BLE001
            if attempt == retries - 1:
                print("    ! %s" % e, file=sys.stderr)
                return None
            time.sleep(2.5 * (attempt + 1))
    return None


def count(where):
    d = sparql(PREFIX + "SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE {\n%s\n}" % where)
    if not d:
        return -1
    try:
        return int(d["results"]["bindings"][0]["n"]["value"])
    except Exception:                                # noqa: BLE001
        return -1


def gene_count(gene):
    # Word-boundary REGEX, not CONTAINS: a substring match counts "TREATMENT"
    # for the gene ATM and "METHOD" for MET, which inflated those two by two
    # orders of magnitude (ATM 10352 -> 36, MET 21736 -> 273).
    return count('?p patent:classificationIPCInventive <%s> ;\n'
                 '   patent:titleOfInvention ?t .\n'
                 'FILTER(REGEX(UCASE(STR(?t)), "\\\\b%s\\\\b"))' % (ONCO, gene))


def class_count(code):
    return count('?p patent:classificationIPCInventive <%s%s> .' % (IPC, code))


def year_count(code, year):
    return count(
        '?p patent:classificationIPCInventive <%s%s> ;\n'
        '   patent:publicationDate ?d .\n'
        'FILTER(?d >= "%d-01-01"^^<http://www.w3.org/2001/XMLSchema#date> '
        '&& ?d < "%d-01-01"^^<http://www.w3.org/2001/XMLSchema#date>)'
        % (IPC, code, year, year + 1))


def top_applicants(limit=400):
    """Sample applicant names in the oncology class and rank them client-side."""
    d = sparql(PREFIX +
               "PREFIX vcard: <http://www.w3.org/2006/vcard/ns#>\n"
               "SELECT ?name WHERE {\n"
               " ?p patent:classificationIPCInventive <%s> ;\n"
               "    patent:applicantVC ?vc . ?vc vcard:fn ?name\n"
               "} LIMIT %d" % (ONCO, limit))
    if not d:
        return []
    tally = {}
    for b in d["results"]["bindings"]:
        nm = clean(b["name"]["value"], 48)
        if nm:
            tally[nm] = tally.get(nm, 0) + 1
    ranked = sorted(tally.items(), key=lambda kv: -kv[1])[:12]
    return [{"name": k, "count": v} for k, v in ranked]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="datasets/patents.json")
    ap.add_argument("--raw", default="datasets/patents_provenance.json")
    args = ap.parse_args()

    print("EPO Linked Open Data — oncology patent landscape")
    print("endpoint:", ENDPOINT)

    print("\n[1/4] gene coverage in IPC A61P35/00 titles (%d genes)" % len(GENES))
    genes = []
    for i, g in enumerate(GENES):
        n = gene_count(g)
        genes.append({"term": g, "index": i, "count": n})
        print("   %-8s %6d" % (g, n))

    print("\n[2/4] modality classes (%d)" % len(CLASSES))
    classes = []
    for i, (code, label, maps_to) in enumerate(CLASSES):
        n = class_count(code)
        classes.append({"code": code, "label": label, "maps_to": maps_to,
                        "index": i, "count": n})
        print("   %-12s %-28s %8d   (%s)" % (code, label, n, maps_to))

    print("\n[3/4] publication velocity in A61P35/00, %d-%d"
          % (YEARS[0], YEARS[-1]))
    velocity = []
    for y in YEARS:
        n = year_count("A61P35-00", y)
        velocity.append({"year": y, "count": n})
        print("   %d %7d" % (y, n))

    print("\n[4/4] leading applicants (sampled)")
    applicants = top_applicants()
    for a in applicants[:6]:
        print("   %-46s %4d" % (a["name"], a["count"]))

    doc = {
        "source": "EPO Linked Open Data SPARQL (data.epo.org/linked-data/query)",
        "retrieved": time.strftime("%Y-%m-%d"),
        "oncology_class": "A61P35-00 antineoplastic agents",
        "n_genes": len(genes),
        "n_classes": len(classes),
        "n_years": len(velocity),
        "year0": YEARS[0],
        "n_applicants": len(applicants),
        "genes": genes,
        "classes": classes,
        "velocity": velocity,
        "applicants": applicants,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(doc, f, indent=1)
    print("\nwrote %s (%d bytes)" % (args.out, os.path.getsize(args.out)))

    raw = sparql(PREFIX +
                 'SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE {\n'
                 ' ?p patent:classificationIPCInventive <%s> ;\n'
                 '    patent:titleOfInvention ?t .\n'
                 ' FILTER(REGEX(UCASE(STR(?t)), "\\\\bEGFR\\\\b"))\n}' % ONCO)
    if raw:
        with open(args.raw, "w") as f:
            json.dump(raw, f, indent=1)
        print("wrote %s (unmodified SPARQL response, provenance)" % args.raw)


if __name__ == "__main__":
    main()
