"""
mapping/utils.py
================
Shared namespaces, URI helper functions, CSV reader, and mode mapping
used by all mapping modules.
"""

import re
import csv
from rdflib import Namespace, URIRef

# ── RDF Namespaces ───────────────────────────────────────────────────────────

LPT    = Namespace("http://example.org/lpt-ontology#")
TM     = Namespace("https://w3id.org/transmodel/commons#")
SCHEMA = Namespace("http://schema.org/")


# ── URI Helper Functions ─────────────────────────────────────────────────────

def sanitise(name: str) -> str:
    """
    Convert a human-readable name into a safe URI local name.
    e.g. "King's Cross St Pancras" → "Kings_Cross_St_Pancras"
         "Harrow & Wealdstone Underground Station" → "Harrow_and_Wealdstone"
    """
    name = re.sub(
        r'\s+(Underground|DLR|Rail|Elizabeth Line|Overground)\s+Station$',
        '', name, flags=re.IGNORECASE
    )
    name = re.sub(r'\s+Station$', '', name, flags=re.IGNORECASE)
    name = name.replace("&", "and").replace("\u2019", "").replace("'", "")
    name = re.sub(r'[^A-Za-z0-9 ]', '', name)
    name = re.sub(r'\s+', '_', name.strip())
    return name


def station_uri(name: str) -> URIRef:
    return LPT[f"station_{sanitise(name)}"]

def line_uri(name: str) -> URIRef:
    return LPT[f"line_{sanitise(name)}"]

def zone_uri(zone_num: int) -> URIRef:
    return LPT[f"Zone{zone_num}"]

def operator_uri(name: str) -> URIRef:
    return LPT[f"operator_{sanitise(name)}"]

def fare_uri(idx: int) -> URIRef:
    return LPT[f"fare_{idx:04d}"]

def fare_product_uri(name: str) -> URIRef:
    return LPT[f"fareproduct_{sanitise(name)}"]

def status_uri(idx: int) -> URIRef:
    return LPT[f"status_{idx:04d}"]

def disruption_uri(idx: int) -> URIRef:
    return LPT[f"disruption_{idx:04d}"]

def accessibility_uri(station_name: str) -> URIRef:
    return LPT[f"stepfree_{sanitise(station_name)}"]

def service_pattern_uri(line_name: str, direction: str) -> URIRef:
    return LPT[f"sp_{sanitise(line_name)}_{sanitise(direction)}"]


# ── Transport Mode Mapping ───────────────────────────────────────────────────

MODE_MAP = {
    "tube":            LPT.Underground,
    "underground":     LPT.Underground,
    "overground":      LPT.Overground,
    "dlr":             LPT.DLR,
    "elizabeth-line":  LPT.ElizabethLineMode,
    "elizabeth line":  LPT.ElizabethLineMode,
    "national-rail":   LPT.NationalRail,
    "national rail":   LPT.NationalRail,
    "bus":             LPT.Bus,
}


def resolve_mode(mode_str: str) -> URIRef:
    """Map a mode string to the corresponding lpt:TransportMode individual."""
    return MODE_MAP.get(mode_str.strip().lower(), LPT.Underground)


# ── CSV Reader ───────────────────────────────────────────────────────────────

def read_csv(filepath: str):
    """Generator yielding rows as dicts, handling BOM and whitespace."""
    with open(filepath, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {k.strip(): (v.strip() if v else '') for k, v in row.items()}