import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from ....core.config import settings
from ....schemas.ship import Ship, ShipDetail, ShipListResponse, ShipTrackResponse
from ....services.aisstream_service import aisstream_service
from ....services.vessel_cache_manager import vessel_cache_manager

router = APIRouter(prefix="/ships", tags=["Ships"])


@router.get("/stream/status", response_model=Dict[str, Any])
async def get_stream_status():
    """
    Returns real-time status of the AISStream WebSocket connection,
    message counts, and vessel cache health.
    """
    status = aisstream_service.get_status()
    cache_info = vessel_cache_manager.get_cache_status(aisstream_connected=aisstream_service.is_connected)
    status.update(cache_info)
    return status


@router.get("", response_model=ShipListResponse)
async def list_ships(
    lamin: Optional[float] = Query(default=None, description="Lower latitude bound"),
    lomin: Optional[float] = Query(default=None, description="Lower longitude bound"),
    lamax: Optional[float] = Query(default=None, description="Upper latitude bound"),
    lomax: Optional[float] = Query(default=None, description="Upper longitude bound"),
    search: Optional[str] = Query(default=None, description="Search vessel name, MMSI, callsign, or destination"),
    ship_type: Optional[str] = Query(default=None, description="Filter by ship type (tanker, cargo, fishing, passenger, tug, military)"),
    operator: Optional[str] = Query(default=None, description="Filter by operator name"),
    min_speed: Optional[float] = Query(default=None, description="Minimum speed in knots"),
    max_speed: Optional[float] = Query(default=None, description="Maximum speed in knots"),
    only_live: Optional[bool] = Query(default=None, description="Filter only vessels updated via live AIS stream"),
):
    """
    Returns list of active maritime vessels matching spatial bounding box and attribute filters.
    Data is served with zero-latency from in-memory registry updated live via AISStream.io.
    """
    ships = vessel_cache_manager.get_ships(
        lamin=lamin,
        lomin=lomin,
        lamax=lamax,
        lomax=lomax,
        search=search,
        ship_type=ship_type,
        operator=operator,
        min_speed=min_speed,
        max_speed=max_speed,
        only_live=only_live,
    )

    return ShipListResponse(
        total=len(vessel_cache_manager._ships),
        count=len(ships),
        time=int(time.time()),
        ships=ships,
        live_stream_connected=aisstream_service.is_connected,
        cached=True,
    )


@router.get("/{ship_id}", response_model=ShipDetail)
async def get_ship_detail(ship_id: str):
    """
    Retrieves complete vessel details, dimensions, navigation status, and voyage info by ID or MMSI.
    """
    detail = vessel_cache_manager.get_ship_detail(ship_id)
    if detail:
        return detail

    raise HTTPException(
        status_code=404,
        detail=f"Vessel '{ship_id}' not found in active fleet registry",
    )


@router.get("/{ship_id}/track", response_model=ShipTrackResponse)
async def get_ship_track(ship_id: str):
    """
    Retrieves historical trajectory waypoints (breadcrumbs / wake) for the specified vessel.
    """
    track = vessel_cache_manager.get_ship_track(ship_id)
    if track:
        return track

    raise HTTPException(
        status_code=404,
        detail=f"Track history for vessel '{ship_id}' not found",
    )
