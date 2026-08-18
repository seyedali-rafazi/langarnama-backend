from typing import List, Optional
from pydantic import BaseModel, Field


class Port(BaseModel):
    id: str = Field(description="Port identifier, e.g. PT001")
    name: str = Field(description="Port commercial name")
    locode: str = Field(description="UN/LOCODE identifier (e.g. IRBND)")
    lat: float = Field(description="Latitude coordinate")
    lon: float = Field(description="Longitude coordinate")
    city: str = Field(description="City or region")
    country: str = Field(default="Iran", description="Country")
    berths: int = Field(default=1, description="Number of active berths/piers")
    maxDraft_m: float = Field(default=10.0, description="Maximum water depth / draft in meters")


class PortListResponse(BaseModel):
    total: int
    ports: List[Port]
