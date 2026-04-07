"""
mapping — CSV-to-RDF mapping modules for the London Public Transport KG.

Modules:
    utils          Shared namespaces, URI helpers, CSV reader
    map_stations   stations.csv  → Station, FareZone individuals
    map_network    network_data.csv → Line, ServicePattern, adjacency
    map_status     service_status.csv → ServiceStatus, DisruptionEvent
    map_fares      fare_price.csv → Fare, FareProduct
    post_process   Interchange / Terminus / Accessible inference
"""

from mapping.map_stations  import map_stations