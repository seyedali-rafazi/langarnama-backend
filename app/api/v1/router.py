from fastapi import APIRouter

from .endpoints.ports import router as ports_router
from .endpoints.ships import router as ships_router
from .endpoints.stations import router as stations_router
from .endpoints.stats import router as stats_router
from .endpoints.websocket import router as websocket_router

api_v1_router = APIRouter()

api_v1_router.include_router(ships_router)
api_v1_router.include_router(ports_router)
api_v1_router.include_router(stations_router)
api_v1_router.include_router(stats_router)
api_v1_router.include_router(websocket_router)
