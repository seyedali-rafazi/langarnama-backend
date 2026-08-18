from fastapi import APIRouter

from ....schemas.stats import StatsResponse
from ....services.aisstream_service import aisstream_service
from ....services.vessel_cache_manager import vessel_cache_manager

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("", response_model=StatsResponse)
async def get_stats():
    """
    Returns summary statistics including active vessel count, type distribution,
    navigation states, ports, coastal stations, and live AIS stream health.
    """
    return vessel_cache_manager.get_stats(
        aisstream_connected=aisstream_service.is_connected
    )
