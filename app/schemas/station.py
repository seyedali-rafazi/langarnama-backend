from typing import List, Literal, Optional
from pydantic import BaseModel, Field

StationType = Literal["VTS", "AIS Base", "Lighthouse", "Coastal Radar"]
StationStatus = Literal["active", "inactive"]


class CoastalStation(BaseModel):
    id: str = Field(description="Station identifier, e.g. CS001")
    name: str = Field(description="Station designation name")
    type: str = Field(description="Station type: VTS, AIS Base, Lighthouse, Coastal Radar")
    lat: float = Field(description="Latitude coordinate")
    lon: float = Field(description="Longitude coordinate")
    frequency: str = Field(default="161.975 MHz", description="VHF/AIS operating frequency")
    range_nm: float = Field(default=30.0, description="Effective coverage range in Nautical Miles")
    operator: str = Field(default="PMO", description="Operating authority (e.g. PMO, NIOC)")
    status: str = Field(default="active", description="Operational status: active / inactive")


class StationListResponse(BaseModel):
    total: int
    stations: List[CoastalStation]
