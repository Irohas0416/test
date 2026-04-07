"""
    - One lpt:Station individual  (stationName, label, locatedInZone, geo)
    - Mode-specific servedBy* links (servedByUndergroundLine, servedByDLR …)
    - lpt:FareZone individuals (created once per unique zone number)
"""

from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

from mapping.utils import (
    LPT, SCHEMA,
    station_uri, zone_uri, resolve_mode, read_csv,
)


def map_stations(g: Graph, filepath: str) -> int:
    """
    Read stations.csv and add Station / FareZone triples to *g*.

    Returns:
        Number of Station individuals created.
    """
    print(f"  Mapping {filepath} ...")
    created_zones: set[int] = set()
    station_count = 0

    for row in read_csv(filepath):
        name = row.get('station_name', '')
        if not name:
            continue

        s = station_uri(name)

        # ── Station type & name ──
        g.add((s, RDF.type, LPT.Station))
        g.add((s, RDF.type, OWL.NamedIndividual))
        g.add((s, LPT.stationName, Literal(name, datatype=XSD.string)))
        g.add((s, RDFS.label, Literal(name)))

        # ── Fare zone ──
        zone_str = row.get('zone', '')
        if zone_str and zone_str != '0':
            try:
                zone_num = int(float(zone_str))
                z = zone_uri(zone_num)
                if zone_num not in created_zones and zone_num >= 1:
                    g.add((z, RDF.type, LPT.FareZone))
                    g.add((z, RDF.type, OWL.NamedIndividual))
                    g.add((z, LPT.zoneNumber, Literal(zone_num, datatype=XSD.integer)))
                    g.add((z, RDFS.label, Literal(f"Zone{zone_num}")))
                    created_zones.add(zone_num)
                g.add((s, LPT.locatedInZone, z))
            except (ValueError, TypeError):
                pass

        # ── Modes → mode-specific servedBy sub-properties ──
        modes_str = row.get('modes', '')
        if modes_str:
            for m in modes_str.split(','):
                m = m.strip().lower()
                if not m:
                    continue
                mode_ind = resolve_mode(m)

                if m in ('tube', 'underground'):
                    g.add((s, LPT.servedByUndergroundLine, mode_ind))
                elif m == 'overground':
                    g.add((s, LPT.servedByOvergroundLine, mode_ind))
                elif m == 'dlr':
                    g.add((s, LPT.servedByDLR, mode_ind))
                elif m in ('elizabeth-line', 'elizabeth line'):
                    g.add((s, LPT.servedByElizabethLine, mode_ind))
                elif m in ('national-rail', 'national rail'):
                    g.add((s, LPT.connectsToService, mode_ind))
                elif m == 'bus':
                    g.add((s, LPT.servedByBusRoute, mode_ind))

        # ── Geo coordinates ──
        lat, lon = row.get('lat', ''), row.get('lon', '')
        if lat and lon:
            try:
                g.add((s, SCHEMA.latitude,  Literal(float(lat), datatype=XSD.double)))
                g.add((s, SCHEMA.longitude, Literal(float(lon), datatype=XSD.double)))
            except ValueError:
                pass

        station_count += 1

    print(f"    → {station_count} Station, {len(created_zones)} FareZone individuals")
    return station_count



if __name__ == "__main__":
    import os
    from rdflib.namespace import OWL as _OWL, RDFS as _RDFS, XSD as _XSD

    ontology_path = "./ontology/KNE_ontology_v03.ttl"
    csv_path      = "./data/stations.csv"
    output_path   = "./ontology/KNE_knowledge_graph_v031.ttl"

    g = Graph()
    g.parse(ontology_path, format="turtle")
    print(f"  TBox loaded: {len(g)} triples from {ontology_path}")

    g.bind("lpt",    LPT)
    g.bind("schema", SCHEMA)
    g.bind("owl",    _OWL)
    g.bind("rdfs",   _RDFS)
    g.bind("xsd",    _XSD)

    if not os.path.exists(csv_path):
        print(f"Error: cannot find {csv_path}")
    else:
        count = map_stations(g, csv_path)
        g.serialize(destination=output_path, format="turtle")
        print(f"Done! {count} stations mapped, total {len(g)} triples → {output_path}")