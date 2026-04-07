from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

from mapping.utils import (
    LPT,
    zone_uri, fare_uri, fare_product_uri, read_csv,
)


def map_fares(g: Graph, filepath: str) -> int:
    """
    Read fare_price.csv and add Fare / FareProduct triples to *g*.

    Returns:
        Number of Fare individuals created.
    """
    print(f"  Mapping {filepath} ...")
    created_products: set[str] = set()
    fare_count = 0

    for idx, row in enumerate(read_csv(filepath)):
        # ── Read every CSV column ──
        product_name = row.get('fare_product', '')      # CSV: fare_product
        amount_str   = row.get('fare_amount', '0')      # CSV: fare_amount
        currency     = row.get('currency', 'GBP')       # CSV: currency
        from_zone    = row.get('applies_from_zone', '')  # CSV: applies_from_zone
        to_zone      = row.get('applies_to_zone', '')    # CSV: applies_to_zone

        if not product_name:
            continue

        # CSV: fare_product → lpt:FareProduct individual (deduplicated)
        #      auto-derive lpt:peakLabel from product name:
        #        "Pay as you go - Off Peak"  → OffPeak
        #        "Pay as you go - Peak"      → Peak
        #        "CashSingle - Anytime"      → Anytime
        #        "Pay as you go - Anytime"   → Anytime
        fp = fare_product_uri(product_name)
        if product_name not in created_products:
            g.add((fp, RDF.type, LPT.FareProduct))
            g.add((fp, RDF.type, OWL.NamedIndividual))
            g.add((fp, RDFS.label, Literal(product_name)))

            lower = product_name.lower()
            if 'off peak' in lower or 'off-peak' in lower:
                label = "OffPeak"
            elif 'peak' in lower:
                label = "Peak"
            else:
                label = "Anytime"
            g.add((fp, LPT.peakLabel, Literal(label, datatype=XSD.string)))

            created_products.add(product_name)

        # CSV: fare_amount       → lpt:fareAmount
        # CSV: currency          → lpt:currency
        # CSV: applies_from_zone → lpt:appliesFromZone → lpt:FareZone
        # CSV: applies_to_zone   → lpt:appliesToZone   → lpt:FareZone
        # CSV: fare_product      → lpt:appliesToProduct → lpt:FareProduct
        f = fare_uri(idx)
        g.add((f, RDF.type, LPT.Fare))
        g.add((f, RDF.type, OWL.NamedIndividual))
        g.add((f, RDFS.label,
               Literal(f"{product_name}: Zone {from_zone}\u2192{to_zone}")))

        # fare_amount
        try:
            g.add((f, LPT.fareAmount,
                   Literal(float(amount_str), datatype=XSD.decimal)))
        except ValueError:
            pass

        # currency
        g.add((f, LPT.currency, Literal(currency, datatype=XSD.string)))

        # appliesToProduct
        g.add((f, LPT.appliesToProduct, fp))

        # appliesFromZone / appliesToZone
        try:
            g.add((f, LPT.appliesFromZone, zone_uri(int(from_zone))))
            g.add((f, LPT.appliesToZone,   zone_uri(int(to_zone))))
        except (ValueError, TypeError):
            pass

        fare_count += 1

    print(f"    → {fare_count} Fare, {len(created_products)} FareProduct individuals")
    return fare_count

if __name__ == "__main__":
    import os
    from rdflib.namespace import OWL as _OWL, RDFS as _RDFS, XSD as _XSD

    prev_step_path = "./ontology/KNE_knowledge_graph_v033.ttl"   # output of map_status
    csv_path       = "./data/fare_price.csv"
    output_path    = "./ontology/KNE_knowledge_graph_v034.ttl"

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
        count = map_fares(g, csv_path)
        g.serialize(destination=output_path, format="turtle")
        print(f"Done! {count} fares mapped, total {len(g)} triples → {output_path}")