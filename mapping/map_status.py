from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

from mapping.utils import (
    LPT,
    line_uri, status_uri, disruption_uri, sanitise, read_csv,
)


def map_service_status(g: Graph, filepath: str) -> int:
    """
    Read service_status.csv and add ServiceStatus / DisruptionEvent
    triples to *g*.

    Returns:
        Number of ServiceStatus individuals created.
    """
    print(f"  Mapping {filepath} ...")
    status_count = 0
    disruption_count = 0

    for idx, row in enumerate(read_csv(filepath)):
        # ── Read every CSV column ──
        entity   = row.get('affected_entity', '')    # CSV: affected_entity
        text     = row.get('status_text', '')         # CSV: status_text
        severity = row.get('severity_level', '')      # CSV: severity_level
        reason   = row.get('closure_reason', '')      # CSV: closure_reason
        start    = row.get('start_date', '')           # CSV: start_date
        end      = row.get('end_date', '')             # CSV: end_date

        if not entity:
            continue

        st = status_uri(idx)
        g.add((st, RDF.type, LPT.ServiceStatus))
        g.add((st, RDF.type, OWL.NamedIndividual))
        g.add((st, LPT.statusText, Literal(text, datatype=XSD.string)))
        g.add((st, RDFS.label, Literal(f"Status: {entity} – {text}")))

        if severity:
            try:
                g.add((st, LPT.severityLevel,
                       Literal(int(severity), datatype=XSD.integer)))
            except ValueError:
                pass

        # Link the affected line → this status via lpt:hasStatus
        l = line_uri(entity)
        g.add((l, LPT.hasStatus, st))

        status_count += 1

        # CSV: closure_reason  → lpt:closureReason on Disruption/Closure
        # CSV: start_date      → lpt:startDate
        # CSV: end_date        → lpt:endDate
 
        if reason:
            de = disruption_uri(idx)
            lower_text = text.lower()
            lower_reason = reason.lower()

            if 'closure' in lower_text or 'closed' in lower_text:
                if end:
                    g.add((de, RDF.type, LPT.TemporaryClosure))
                else:
                    g.add((de, RDF.type, LPT.PermanentClosure))
            elif 'severe' in lower_text or 'severe' in lower_reason:
                g.add((de, RDF.type, LPT.SevereDelay))
            else:
                g.add((de, RDF.type, LPT.DisruptionEvent))

            g.add((de, RDF.type, OWL.NamedIndividual))
            g.add((de, LPT.closureReason, Literal(reason, datatype=XSD.string)))
            g.add((de, RDFS.label, Literal(f"Disruption: {entity}")))

            if start:
                g.add((de, LPT.startDate, Literal(start, datatype=XSD.date)))
            if end:
                g.add((de, LPT.endDate, Literal(end, datatype=XSD.date)))

            # Synthetic RouteSegment so the disruption satisfies the axiom:
            #   DisruptionEvent ⊑ ∃affectsSegment.RouteSegment
            seg = LPT[f"segment_{sanitise(entity)}"]
            g.add((seg, RDF.type, LPT.RouteSegment))
            g.add((seg, RDF.type, OWL.NamedIndividual))
            g.add((seg, LPT.onLine, l))
            g.add((seg, RDFS.label, Literal(f"Segment on {entity}")))
            g.add((de, LPT.affectsSegment, seg))

            disruption_count += 1

    print(f"    → {status_count} ServiceStatus, {disruption_count} DisruptionEvent/ClosureEvent")
    return status_count


if __name__ == "__main__":
    import os
    from rdflib.namespace import OWL as _OWL, RDFS as _RDFS, XSD as _XSD

    prev_step_path = "./ontology/KNE_knowledge_graph_v032.ttl"   # output of map_network
    csv_path       = "./data/service_status.csv"
    output_path    = "./ontology/KNE_knowledge_graph_v033.ttl"

    g = Graph()
    g.parse(prev_step_path, format="turtle")
    print(f"  Loaded previous step: {len(g)} triples from {prev_step_path}")

    g.bind("lpt",  LPT)
    g.bind("owl",  _OWL)
    g.bind("rdfs", _RDFS)
    g.bind("xsd",  _XSD)

    if not os.path.exists(csv_path):
        print(f"Error: cannot find {csv_path}")
    else:
        count = map_service_status(g, csv_path)
        g.serialize(destination=output_path, format="turtle")
        print(f"Done! {count} statuses mapped, total {len(g)} triples → {output_path}")