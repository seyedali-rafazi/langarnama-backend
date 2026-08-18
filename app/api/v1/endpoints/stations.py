from typing import Optional
from fastapi import APIRouter, HTTPException

from ....schemas.station import CoastalStation, StationListResponse
from ....services.reference_data_service import reference_data_service

router = APIRouter(prefix="/stations", tags=["Coastal Stations"])


@router.get("", response_model=StationListResponse)
async def list_stations():
    """
    Returns reference list of coastal AIS receivers, VTS traffic control centers, and lighthouses.
    """
    stations = reference_data_service.get_stations()
    return StationListResponse(total=len(stations), stations=stations)


@router.get("/{station_id}", response_model=CoastalStation)
async def get_station(station_id: str):
    """
    Retrieves coastal station by ID (e.g. CS001) or name.
    """
    station = reference_data_service.get_station_by_id(station_id)
    if station:
        return station
    raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found")
