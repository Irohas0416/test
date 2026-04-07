"""
Fix OOPS! pitfalls in the London Public Transport ontology — v2.

Fixes (and corrections to v1):
- P10: Connect tm:Line via equivalentClass; tm:StopPlace via subClassOf chain
- P11: Missing domain/range on properties
- P13: Missing inverse relationships
- P26: schema:name http/https and schema:startDate http/https declared equivalent
- P27: Remove wrong owl:equivalentProperty between lpt:startDate and schema:startDate
- P28: Remove wrong SymmetricProperty on interchangesWith; use proper inverse instead
- P30: Equivalent class declarations for schema:Place
- P31: Remove wrong equivalentClass between tm:StopPlace and lpt:Station

Usage:
    python fix_ontology.py --input ontology/KNE_knowledge_graph_v034.ttl --output ontology/KNE_knowledge_graph_v034.ttl
"""

import argparse
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

LPT = Namespace("http://example.org/lpt-ontology#")
TM = Namespace("https://w3id.org/transmodel/commons#")
SCHEMA_HTTP = Namespace("http://schema.org/")
SCHEMA_HTTPS = Namespace("https://schema.org/")


def remove_previous_bad_fixes(g: Graph):
    """Remove triples that v1 of this script added incorrectly, AND any bad triples from the original file."""
    print("[CLEANUP] Removing incorrect triples from previous run / original file...")

    # P28: interchangesWith should NOT be symmetric (domain Station, range ServicePattern)
    g.remove((LPT.interchangesWith, RDF.type, OWL.SymmetricProperty))

    # P31: tm:StopPlace is NOT equivalent to lpt:Station (StopPlace is broader)
    g.remove((TM.StopPlace, OWL.equivalentClass, LPT.Station))
    g.remove((LPT.Station, OWL.equivalentClass, TM.StopPlace))

    # P27: lpt:startDate should not be owl:equivalentProperty with schema:startDate
    g.remove((LPT.startDate, OWL.equivalentProperty, SCHEMA_HTTP.startDate))
    g.remove((LPT.startDate, OWL.equivalentProperty, SCHEMA_HTTPS.startDate))
    g.remove((SCHEMA_HTTP.startDate, OWL.equivalentProperty, LPT.startDate))
    g.remove((SCHEMA_HTTPS.startDate, OWL.equivalentProperty, LPT.startDate))

    print("  - removed: interchangesWith SymmetricProperty")
    print("  - removed: tm:StopPlace ≡ lpt:Station")
    print("  - removed: lpt:startDate ≡ schema:startDate")


def add_p10_fixes(g: Graph):
    """P10: Connect isolated tm:Line. For tm:StopPlace, use subClassOf chain instead."""
    print("\n[P10] Connecting isolated external classes...")

    # tm:Line and lpt:Line are conceptually the same — equivalence is fine
    g.add((TM.Line, OWL.equivalentClass, LPT.Line))
    print("  + tm:Line  owl:equivalentClass  lpt:Line")

    # tm:StopPlace is a broader concept. We DON'T declare equivalence.
    # Instead, ensure lpt:Stop also extends tm:StopPlace so the relation is bidirectionally
    # populated through the existing subClassOf hierarchy.
    g.add((LPT.Stop, RDFS.subClassOf, TM.StopPlace))
    print("  + lpt:Stop  rdfs:subClassOf  tm:StopPlace  (P10 — keeps StopPlace connected)")


def add_p11_fixes(g: Graph):
    """P11: Add domain and range to properties that lack them."""
    print("\n[P11] Adding missing domain/range...")

    g.add((LPT.servedByBusRoute, RDFS.domain, LPT.Place))
    print("  + servedByBusRoute  domain  lpt:Place")

    for prop in ["servedByDLR", "servedByUndergroundLine",
                 "servedByOvergroundLine", "servedByElizabethLine"]:
        g.add((LPT[prop], RDFS.domain, LPT.Place))
        g.add((LPT[prop], RDFS.range, LPT.TransportMode))
        print(f"  + {prop}  domain lpt:Place  range lpt:TransportMode")

    g.add((LPT.hasStepFreeStreetToTrainFeature, RDFS.domain, LPT.Station))
    g.add((LPT.hasStepFreeStreetToTrainFeature, RDFS.range, LPT.StepFreeAccess))
    print("  + hasStepFreeStreetToTrainFeature  domain lpt:Station  range lpt:StepFreeAccess")

    g.add((LPT.hasDirectNationalRailConnection, RDFS.domain, LPT.Station))
    g.add((LPT.hasDirectNationalRailConnection, RDFS.range, LPT.Station))
    print("  + hasDirectNationalRailConnection  domain lpt:Station  range lpt:Station")

    for ns in (SCHEMA_HTTP, SCHEMA_HTTPS):
        g.add((ns.name, RDFS.domain, OWL.Thing))
        g.add((ns.name, RDFS.range, XSD.string))
        g.add((ns.startDate, RDFS.domain, OWL.Thing))
        g.add((ns.startDate, RDFS.range, XSD.date))
    print("  + schema:name  domain owl:Thing  range xsd:string")
    print("  + schema:startDate  domain owl:Thing  range xsd:date")


def add_p13_fixes(g: Graph):
    """P13: Declare inverse relationships."""
    print("\n[P13] Adding inverse properties...")

    # OOPS!'s own suggestion: hasStop ↔ servedBy
    g.add((LPT.hasStop, OWL.inverseOf, LPT.servedBy))
    print("  + hasStop  owl:inverseOf  servedBy")

    # interchangesWith now gets a normal inverse (NOT symmetric)
    # It goes Station → ServicePattern, so inverse goes ServicePattern → Station
    g.add((LPT.serviceInterchangeableAt, RDF.type, OWL.ObjectProperty))
    g.add((LPT.serviceInterchangeableAt, RDFS.label, Literal("serviceInterchangeableAt")))
    g.add((LPT.serviceInterchangeableAt, RDFS.comment,
           Literal("Inverse of interchangesWith. Indicates that this service pattern can be interchanged at the given station.")))
    g.add((LPT.serviceInterchangeableAt, RDFS.domain, LPT.ServicePattern))
    g.add((LPT.serviceInterchangeableAt, RDFS.range, LPT.Station))
    g.add((LPT.interchangesWith, OWL.inverseOf, LPT.serviceInterchangeableAt))
    g.add((LPT.serviceInterchangeableAt, OWL.inverseOf, LPT.interchangesWith))
    print("  + interchangesWith  owl:inverseOf  serviceInterchangeableAt")

    inverses = [
        ("hasMode", "isModeOf",
         "Inverse of hasMode.", LPT.TransportMode, LPT.ServicePattern),
        ("onLine", "hasEntityOnLine",
         "Inverse of onLine.", LPT.Line, LPT.TransportEntity),
        ("locatedInZone", "containsPlace",
         "Inverse of locatedInZone.", LPT.FareZone, LPT.Place),
        ("hasAccessibilityFeature", "isAccessibilityFeatureOf",
         "Inverse of hasAccessibilityFeature.", LPT.AccessibilityFeature, LPT.Station),
        ("hasClosureEvent", "isClosureEventOf",
         "Inverse of hasClosureEvent.", LPT.ClosureEvent, LPT.Station),
        ("hasConnection", "isConnectionAt",
         "Inverse of hasConnection.", LPT.Connection, LPT.Station),
        ("hasIntermediateStation", "isIntermediateStationOf",
         "Inverse of hasIntermediateStation.", LPT.Station, LPT.JourneyOption),
        ("hasStatus", "isStatusOf",
         "Inverse of hasStatus.", LPT.ServiceStatus, LPT.ServicePattern),
        ("affectsSegment", "isAffectedByDisruption",
         "Inverse of affectsSegment.", LPT.RouteSegment, LPT.DisruptionEvent),
        ("connectsToService", "serviceConnectsAt",
         "Inverse of connectsToService.", LPT.RailService, LPT.Station),
        ("requiresChangeAt", "isChangePointFor",
         "Inverse of requiresChangeAt.", LPT.Station, LPT.JourneyOption),
        ("usesService", "isUsedByJourney",
         "Inverse of usesService.", LPT.ServicePattern, LPT.JourneyOption),
        ("partOfBranch", "hasBranchEntity",
         "Inverse of partOfBranch.", LPT.Branch, LPT.TransportEntity),
        ("passesThroughHub", "isHubFor",
         "Inverse of passesThroughHub.", LPT.Hub, LPT.BusRoute),
        ("appliesFromZone", "isFromZoneOf",
         "Inverse of appliesFromZone.", LPT.FareZone, LPT.Fare),
        ("appliesToZone", "isToZoneOf",
         "Inverse of appliesToZone.", LPT.FareZone, LPT.Fare),
        ("appliesToProduct", "isProductInFare",
         "Inverse of appliesToProduct.", LPT.FareProduct, LPT.Fare),
        ("validDuring", "validityFor",
         "Inverse of validDuring.", LPT.OperatingPeriod, LPT.TransportEntity),
        ("startsAt", "isStartOf",
         "Inverse of startsAt.", LPT.Station, LPT.TransportEntity),
        ("endsAt", "isEndOf",
         "Inverse of endsAt.", LPT.Station, LPT.TransportEntity),
        ("servesArea", "areaServedBy",
         "Inverse of servesArea.", LPT.Place, LPT.BusRoute),
        ("servedByDLR", "isDLRModeFor",
         "Inverse of servedByDLR.", LPT.TransportMode, LPT.Place),
        ("servedByUndergroundLine", "isUndergroundModeFor",
         "Inverse of servedByUndergroundLine.", LPT.TransportMode, LPT.Place),
        ("servedByOvergroundLine", "isOvergroundModeFor",
         "Inverse of servedByOvergroundLine.", LPT.TransportMode, LPT.Place),
        ("servedByElizabethLine", "isElizabethLineModeFor",
         "Inverse of servedByElizabethLine.", LPT.TransportMode, LPT.Place),
        ("servedByBusRoute", "isBusRouteFor",
         "Inverse of servedByBusRoute.", LPT.BusRoute, LPT.Place),
        ("hasStepFreeStreetToTrainFeature", "isStepFreeStreetToTrainFeatureOf",
         "Inverse of hasStepFreeStreetToTrainFeature.", LPT.StepFreeAccess, LPT.Station),
    ]

    for prop_name, inv_name, comment, dom, rng in inverses:
        prop = LPT[prop_name]
        inv = LPT[inv_name]
        g.add((inv, RDF.type, OWL.ObjectProperty))
        g.add((inv, RDFS.label, Literal(inv_name)))
        g.add((inv, RDFS.comment, Literal(comment)))
        g.add((inv, RDFS.domain, dom))
        g.add((inv, RDFS.range, rng))
        g.add((prop, OWL.inverseOf, inv))
        g.add((inv, OWL.inverseOf, prop))
        print(f"  + {prop_name}  owl:inverseOf  {inv_name}")


def add_p26_fixes(g: Graph):
    """P26: Declare http and https variants of schema properties as equivalent."""
    print("\n[P26] Declaring schema:name and schema:startDate http/https equivalents...")

    g.add((SCHEMA_HTTP.name, OWL.equivalentProperty, SCHEMA_HTTPS.name))
    g.add((SCHEMA_HTTPS.name, OWL.equivalentProperty, SCHEMA_HTTP.name))
    print("  + http://schema.org/name  ≡  https://schema.org/name")

    g.add((SCHEMA_HTTP.startDate, OWL.equivalentProperty, SCHEMA_HTTPS.startDate))
    g.add((SCHEMA_HTTPS.startDate, OWL.equivalentProperty, SCHEMA_HTTP.startDate))
    print("  + http://schema.org/startDate  ≡  https://schema.org/startDate")


def add_p27_fixes(g: Graph):
    """P27: Replace wrong equivalentProperty with subPropertyOf."""
    print("\n[P27] Fixing lpt:startDate relation to schema:startDate...")

    # The (incorrect) equivalentProperty triple was already removed in cleanup.
    # Now declare the correct relationship: lpt:startDate is a sub-property of schema:startDate.
    g.add((LPT.startDate, RDFS.subPropertyOf, SCHEMA_HTTP.startDate))
    print("  + lpt:startDate  rdfs:subPropertyOf  schema:startDate")


def add_p30_fixes(g: Graph):
    """P30: Declare equivalent classes for schema:Place across http/https variants."""
    print("\n[P30] Adding equivalent class declarations for Place...")
    g.add((LPT.Place, OWL.equivalentClass, SCHEMA_HTTPS.Place))
    g.add((SCHEMA_HTTP.Place, OWL.equivalentClass, SCHEMA_HTTPS.Place))
    print("  + lpt:Place  owl:equivalentClass  https://schema.org/Place")
    print("  + http://schema.org/Place  owl:equivalentClass  https://schema.org/Place")


def detect_format(filename: str) -> str:
    """Detect rdflib format from file extension."""
    name = filename.lower()
    if name.endswith(".ttl"):
        return "turtle"
    if name.endswith(".rdf") or name.endswith(".owl") or name.endswith(".xml"):
        return "xml"
    if name.endswith(".nt"):
        return "nt"
    if name.endswith(".jsonld") or name.endswith(".json"):
        return "json-ld"
    return "turtle"


def main():
    parser = argparse.ArgumentParser(
        description="Apply OOPS! pitfall fixes to the LPT ontology (v2)."
    )
    parser.add_argument("--input", required=True, help="Input ontology file")
    parser.add_argument("--output", required=True, help="Output file (same path = overwrite)")
    parser.add_argument("--patch", help="Optional: also write a Turtle patch file")
    args = parser.parse_args()

    input_format = detect_format(args.input)
    output_format = detect_format(args.output)

    print(f"Loading {args.input} (format: {input_format})...")
    g = Graph()
    g.parse(args.input, format=input_format)
    initial_count = len(g)
    print(f"Loaded {initial_count} triples\n")

    original = set(g)

    remove_previous_bad_fixes(g)
    add_p10_fixes(g)
    add_p11_fixes(g)
    add_p13_fixes(g)
    add_p26_fixes(g)
    add_p27_fixes(g)
    add_p30_fixes(g)

    final_count = len(g)
    delta = final_count - initial_count
    print(f"\n{'='*60}")
    print(f"Net change: {delta:+d} triples (total: {final_count})")

    g.bind("lpt", LPT)
    g.bind("tm", TM)
    g.bind("schema", SCHEMA_HTTPS)
    g.bind("schema1", SCHEMA_HTTP)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    print(f"\nWriting fixed ontology to {args.output} (format: {output_format})...")
    g.serialize(destination=args.output, format=output_format)
    print("Done.")

    if args.patch:
        patch_graph = Graph()
        patch_graph.bind("lpt", LPT)
        patch_graph.bind("tm", TM)
        patch_graph.bind("schema", SCHEMA_HTTPS)
        patch_graph.bind("schema1", SCHEMA_HTTP)
        patch_graph.bind("owl", OWL)
        patch_graph.bind("rdfs", RDFS)
        patch_graph.bind("xsd", XSD)
        for triple in g:
            if triple not in original:
                patch_graph.add(triple)
        patch_graph.serialize(destination=args.patch, format="turtle")
        print(f"Patch (Turtle) saved to {args.patch}")


if __name__ == "__main__":
    main()