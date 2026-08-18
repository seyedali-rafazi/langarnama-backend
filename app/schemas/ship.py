from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

ShipType = Literal["tanker", "cargo", "fishing", "passenger", "tug", "military"]


class Ship(BaseModel):
    id: str = Field(description="Unique vessel identifier (e.g. SH1001 or MMSI)")
    name: str = Field(description="Vessel name")
    mmsi: str = Field(description="Maritime Mobile Service Identity")
    operator: str = Field(default="Independent", description="Vessel owner or operator")
    shipType: ShipType = Field(default="cargo", description="Standard vessel category")
    lat: float = Field(description="Latitude in decimal degrees")
    lon: float = Field(description="Longitude in decimal degrees")
    heading_deg: float = Field(default=0.0, description="Heading in degrees (0-360)")
    speed_kts: float = Field(default=0.0, description="Speed over ground in knots")
    draft_m: float = Field(default=6.0, description="Maximum draught in meters")
    length_m: float = Field(default=120.0, description="Vessel length in meters")
    beam_m: Optional[float] = Field(default=None, description="Vessel beam / width in meters")
    callsign: Optional[str] = Field(default=None, description="Radio call sign")
    imo: Optional[int] = Field(default=None, description="IMO number")
    nav_status: Optional[str] = Field(default=None, description="Navigational status")
    origin_port: str = Field(default="Unknown", description="Origin port or terminal")
    destination_port: str = Field(default="In Transit", description="Reported destination")
    eta: Optional[str] = Field(default=None, description="Estimated time of arrival")
    path: List[List[float]] = Field(
        default_factory=list,
        description="List of recent waypoints [[lat, lon], ...] for track/wake visualization",
    )
    lastUpdate: str = Field(description="ISO 8601 UTC timestamp of last AIS report")
    country: Optional[str] = Field(default=None, description="Flag / country of registration")
    flag: Optional[str] = Field(default=None, description="Flag emoji or 2-letter code")


class ShipDetail(Ship):
    rot: Optional[float] = Field(default=None, description="Rate of turn")
    cog: Optional[float] = Field(default=None, description="Course over ground")
    sog: Optional[float] = Field(default=None, description="Speed over ground")
    dimension_a: Optional[int] = Field(default=None, description="Distance from bow to reference point")
    dimension_b: Optional[int] = Field(default=None, description="Distance from stern to reference point")
    dimension_c: Optional[int] = Field(default=None, description="Distance from port to reference point")
    dimension_d: Optional[int] = Field(default=None, description="Distance from starboard to reference point")
    is_live: bool = Field(default=True, description="True if received via live AISStream stream")


class ShipListResponse(BaseModel):
    total: int = Field(description="Total vessels in system")
    count: int = Field(description="Number of vessels matching current filters")
    time: int = Field(description="Server epoch timestamp")
    ships: List[Ship] = Field(description="List of vessel records")
    live_stream_connected: bool = Field(default=True, description="AISStream WebSocket connection status")
    cached: bool = Field(default=True, description="Served from memory cache")


class ShipTrackResponse(BaseModel):
    ship_id: str
    mmsi: str
    name: str
    shipType: str
    points: List[List[float]] = Field(description="Waypoint coordinates [[lat, lon], ...]")
    count: int
    last_update: str
