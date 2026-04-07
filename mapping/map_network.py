from collections import defaultdict

from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

from mapping.utils import (
    LPT,
    station_uri, line_uri, operator_uri,
    service_pattern_uri, accessibility_uri,
    resolve_mode, read_csv,
)


def map_network(g: Graph, filepath: str) -> int:
    """
    Read network_data.csv and add Line / ServicePattern / Operator /
    adjacency / accessibility triples to *g*.

    Returns:
        Number of Line individuals created.
    """
    print(f"  Mapping {filepath} ...")

    sequences: dict[tuple, list] = defaultdict(list)
    line_modes: dict[str, str] = {}          # line_name → transport_mode
    line_operators: dict[str, str] = {}      # line_name → operator_name
    step_free_stations: set[str] = set()     # station names with step-free = True

    for row in read_csv(filepath):
        line_name = row.get('line_name', '')                                  # CSV: line_name
        direction = row.get('direction_name', '')                             # CSV: direction_name
        stn_name  = row.get('station_name', '')                               # CSV: station_name
        mode      = row.get('transport_mode', '')                             # CSV: transport_mode
        operator  = row.get('operator_name', '')                              # CSV: operator_name
        step_free = row.get('is_step_free_street_to_train', '').lower() == 'true'  # CSV: is_step_free_street_to_train

        if not line_name or not stn_name:
            continue

        try:
            seq_num = int(row.get('sequence_number', '0'))                    # CSV: sequence_number
        except ValueError:
            seq_num = 0

        sequences[(line_name, direction)].append((seq_num, stn_name, step_free))
        line_modes[line_name] = mode
        if operator:
            line_operators[line_name] = operator
        if step_free:
            step_free_stations.add(stn_name)

    # CSV: line_name       → lpt:Line individual with lpt:lineName
    # CSV: transport_mode  → lpt:hasMode linking Line to TransportMode
    line_count = 0
    for ln, mode_str in line_modes.items():
        l = line_uri(ln)
        g.add((l, RDF.type, LPT.Line))
        g.add((l, RDF.type, OWL.NamedIndividual))
        g.add((l, LPT.lineName, Literal(ln, datatype=XSD.string)))
        g.add((l, RDFS.label, Literal(ln)))
        g.add((l, LPT.hasMode, resolve_mode(mode_str)))
        line_count += 1


    # CSV: operator_name   → lpt:Operator individual with lpt:operatorName
    #                        lpt:operatedBy linking Line → Operator
    created_ops: set[str] = set()
    for ln, op_name in line_operators.items():
        if not op_name:
            continue
        if op_name not in created_ops:
            o = operator_uri(op_name)
            g.add((o, RDF.type, LPT.Operator))
            g.add((o, RDF.type, OWL.NamedIndividual))
            g.add((o, LPT.operatorName, Literal(op_name, datatype=XSD.string)))
            g.add((o, RDFS.label, Literal(op_name)))
            created_ops.add(op_name)
        g.add((line_uri(ln), LPT.operatedBy, operator_uri(op_name)))

    # CSV: direction_name    → lpt:directionName on ServicePattern
    # CSV: sequence_number   → sort order for adjacency chain
    #                          + lpt:sequenceNumber data property
    # CSV: station_name      → lpt:hasStop, lpt:servedBy,
    #                          lpt:nextStation / lpt:previousStation chain,
    #                          lpt:startsAt / lpt:endsAt (termini)
    sp_count = 0
    for (ln, direction), stops in sequences.items():
        stops.sort(key=lambda x: x[0])  # sort by sequence_number

        sp = service_pattern_uri(ln, direction)
        l  = line_uri(ln)

        g.add((sp, RDF.type, LPT.ServicePattern))
        g.add((sp, RDF.type, OWL.NamedIndividual))
        g.add((sp, LPT.onLine, l))
        g.add((sp, LPT.directionName, Literal(direction, datatype=XSD.string)))
        g.add((sp, RDFS.label, Literal(f"{ln} ({direction})")))

        if ln in line_modes:
            g.add((sp, LPT.hasMode, resolve_mode(line_modes[ln])))

        # Ordered stops + nextStation / previousStation adjacency chain
        prev_uri = None
        for seq_num, stn_name, _ in stops:
            stn = station_uri(stn_name)
            g.add((sp, LPT.hasStop, stn))
            g.add((stn, LPT.servedBy, sp))

            # CSV: sequence_number → data property on station
            g.add((stn, LPT.sequenceNumber, Literal(seq_num, datatype=XSD.integer)))

            # Build nextStation / previousStation chain
            if prev_uri is not None:
                g.add((prev_uri, LPT.nextStation, stn))
                g.add((stn, LPT.previousStation, prev_uri))
            prev_uri = stn

        # Mark terminus ends of the service pattern
        if stops:
            g.add((sp, LPT.startsAt, station_uri(stops[0][1])))
            g.add((sp, LPT.endsAt,   station_uri(stops[-1][1])))

        sp_count += 1

    # CSV: is_step_free_street_to_train → lpt:StepFreeAccess individual
    #      lpt:hasAccessibilityFeature linking Station → StepFreeAccess
    #      lpt:isStepFreeStreetToTrain = true
    acc_count = 0
    for stn_name in step_free_stations:
        stn = station_uri(stn_name)
        acc = accessibility_uri(stn_name)
        g.add((acc, RDF.type, LPT.StepFreeAccess))
        g.add((acc, RDF.type, OWL.NamedIndividual))
        g.add((acc, LPT.isStepFreeStreetToTrain, Literal(True, datatype=XSD.boolean)))
        g.add((acc, RDFS.label, Literal(f"StepFreeAccess at {stn_name}")))
        g.add((stn, LPT.hasAccessibilityFeature, acc))
        acc_count += 1

    print(f"    → {line_count} Line, {sp_count} ServicePattern, "
          f"{len(created_ops)} Operator, {acc_count} StepFreeAccess")
    return line_count

if __name__ == "__main__":
    import os
    from rdflib.namespace import OWL as _OWL, RDFS as _RDFS, XSD as _XSD

    prev_step_path = "./ontology/KNE_knowledge_graph_v031.ttl"   # output of map_stations
    csv_path       = "./data/network_data.csv"
    output_path    = "./ontology/KNE_knowledge_graph_v032.ttl"

    g = Graph()
    g.parse(prev_step_path, format="turtle")
    print(f"  Loaded previous step: {len(g)} triples from {prev_step_path}")

    g.bind("lpt",    LPT)
    g.bind("owl",    _OWL)
    g.bind("rdfs",   _RDFS)
    g.bind("xsd",    _XSD)

    if not os.path.exists(csv_path):
        print(f"Error: cannot find {csv_path}")
    else:
        count = map_network(g, csv_path)
        g.serialize(destination=output_path, format="turtle")
        print(f"Done! {count} lines mapped, total {len(g)} triples → {output_path}")