from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import date

# -------------------------------------------------------------------------
# 1. Network Topology CSV Structure
# Represents stations, the lines that serve them, and accessibility features.
# -------------------------------------------------------------------------
class NetworkTopologyCSVRow(BaseModel):
    station_name: str = Field(..., description="Human-readable station name (maps to lpt:stationName).")
    line_name: str = Field(..., description="Human-readable line name like 'Jubilee' (maps to lpt:lineName).")
    transport_mode: str = Field(..., description="Mode of transport: Underground, Bus, DLR, NationalRail, etc. (maps to lpt:TransportMode individuals).")
    operator_name: Optional[str] = Field(None, description="Human-readable operator name (maps to lpt:operatorName).")
    # zone_number: Optional[int] = Field(None, description="Fare zone number, e.g., 1 to 6 (maps to lpt:zoneNumber).")
    is_step_free_street_to_train: Optional[bool] = Field(None, description="Whether the station offers step-free access from street to train (maps to lpt:isStepFreeStreetToTrain).")
    sequence_number: Optional[int] = Field(None, description="Order position in the route or line (maps to lpt:sequenceNumber).")
    direction_name: Optional[str] = Field(None, description="Direction label such as eastbound or northbound (maps to lpt:directionName).")

# -------------------------------------------------------------------------
# 2. Service Status & Disruption CSV Structure
# Represents delays, closures, and the affected transport entities.
# -------------------------------------------------------------------------
class ServiceStatusCSVRow(BaseModel):
    affected_entity: str = Field(..., description="The name of the Station, Line, or RouteSegment affected by the event.")
    status_text: str = Field(..., description="Textual description of service status (maps to lpt:statusText).")
    severity_level: Optional[int] = Field(None, description="Severity level of the service status (maps to lpt:severityLevel).")
    closure_reason: Optional[str] = Field(None, description="The stated reason for a closure event (maps to lpt:closureReason).")
    start_date: Optional[date] = Field(None, description="Start date for the period or event (maps to lpt:startDate).")
    end_date: Optional[date] = Field(None, description="End date for the period or event (maps to lpt:endDate).")

# -------------------------------------------------------------------------
# 3. Fares CSV Structure
# Represents pricing rules between zones or for specific products.
# -------------------------------------------------------------------------
class FareCSVRow(BaseModel):
    fare_product: str = Field(..., description="Fare product such as Oyster adult peak (maps to lpt:FareProduct).")
    fare_amount: float = Field(..., description="Fare amount (maps to lpt:fareAmount).")
    currency: str = Field(default="GBP", description="Currency code or label (maps to lpt:currency).")
    applies_from_zone: int = Field(..., description="Start fare zone number (maps to lpt:appliesFromZone).")
    applies_to_zone: int = Field(..., description="End fare zone number (maps to lpt:appliesToZone).")

# -------------------------------------------------------------------------
# Root Extraction Model (If using LLMs to extract unstructured text into rows)
# -------------------------------------------------------------------------
class TransportExtractionData(BaseModel):
    network_records: List[NetworkTopologyCSVRow] = Field(default_factory=list, description="Extracted routing, station, and line data.")
    status_records: List[ServiceStatusCSVRow] = Field(default_factory=list, description="Extracted service status and closure events.")
    fare_records: List[FareCSVRow] = Field(default_factory=list, description="Extracted fare and pricing data.")

class StationCSVRow(BaseModel):
    naptan_id: str = Field(..., description="The TfL Naptan ID of the station.")
    station_name: str = Field(..., description="The common name of the station.")
    modes: str = Field(..., description="Comma-separated list of transport modes available.")
    zone: Optional[int] = Field(None, description="Zone number, if applicable")
    lat: Optional[float] = Field(None, description="Latitude coordinate.")
    lon: Optional[float] = Field(None, description="Longitude coordinate.")

# Not Added Yet

class AccessibilityRecord(BaseModel):
    station_name: str = Field(..., description="Name of the station (e.g., 'Green Park')")
    is_step_free_street_to_train: bool = Field(..., description="True if step-free access from street to train is available")
    
    # Optional fields if you plan to expand accessibility features later
    feature_description: str | None = Field(default=None, description="Detailed description of the access")

class BranchTerminusRecord(BaseModel):
    line_name: str = Field(..., description="The parent line (e.g., 'Northern')")
    branch_name: str = Field(..., description="The specific branch (e.g., 'Edgware Branch')")
    terminus_station: str = Field(..., description="The station acting as the terminus for this branch")

class BusNetworkRecord(BaseModel):
    route_number: str = Field(..., description="The bus route identifier (e.g., '148', 'N9')")
    stop_name: str = Field(..., description="Name of the bus stop")
    sequence_number: int = Field(..., description="Order of the stop in the route")
    is_hub: bool = Field(default=False, description="True if the stop is a major interchange Hub")
    serves_area: str | None = Field(default=None, description="General area served by the route/stop (e.g., 'Camberwell')")

class ConnectionRecord(BaseModel):
    from_station: str = Field(..., description="Origin station of the connection")
    to_station: str = Field(..., description="Destination station of the connection")
    connection_type: Literal["direct", "national_rail", "interchange"] = Field(..., description="Type of physical connection")
    requires_line_change: bool = Field(default=True, description="Does traversing this connection constitute a line change?")
    walking_time_minutes: int | None = Field(default=None, description="Optional walking time for the connection")

class ServiceFrequencyRecord(BaseModel):
    service_pattern_or_line: str = Field(..., description="The Line or Service Pattern this applies to")
    operating_period: str = Field(..., description="E.g., 'Weekday Peak', 'Sunday Off-Peak'")
    operating_hours_text: str = Field(..., description="Text description of hours (e.g., '06:30 - 09:30')")
    frequency_minutes: float = Field(..., description="Train frequency in minutes during this period")

# complete
class StationClosureRecord(BaseModel):
    station_name: str = Field(..., description="The specific station that is closed")
    closure_reason: str = Field(..., description="Reason for the station closure")
    start_date: date = Field(..., description="Start date of the closure (YYYY-MM-DD)")
    # end_date: date = Field(..., description="End date of the closure (YYYY-MM-DD)")
    
    # If end_date is missing, your mapping script can classify it as a PermanentClosure
    end_date: date | None = Field(default=None, description="End date of the closure. Leave blank if permanent.")