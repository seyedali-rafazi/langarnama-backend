import asyncio
import json
import time
from typing import Any, Dict, Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ....core.config import settings
from ....core.logging import logger
from ....schemas.ship import ShipListResponse
from ....services.aisstream_service import aisstream_service
from ....services.vessel_cache_manager import vessel_cache_manager

router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ClientConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Frontend WebSocket client connected. Active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Frontend WebSocket client disconnected. Active clients: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


manager = ClientConnectionManager()


@router.websocket("/live")
async def websocket_live_vessels(
    websocket: WebSocket,
    lamin: Optional[float] = None,
    lomin: Optional[float] = None,
    lamax: Optional[float] = None,
    lomax: Optional[float] = None,
    ship_type: Optional[str] = None,
):
    """
    WebSocket endpoint streaming real-time vessel positions to frontend map clients.
    Clients can supply initial bounding box query parameters or send JSON messages
    such as `{"lamin": 25.0, "lomin": 50.0, "lamax": 30.0, "lomax": 60.0, "ship_type": "tanker"}`
    to dynamically adapt the stream to viewport movements.
    """
    await manager.connect(websocket)

    filters: Dict[str, Any] = {
        "lamin": lamin,
        "lomin": lomin,
        "lamax": lamax,
        "lomax": lomax,
        "ship_type": ship_type,
        "search": None,
    }

    filter_updated_event = asyncio.Event()

    async def listen_for_client_messages():
        nonlocal filters
        try:
            while True:
                msg = await websocket.receive_text()
                try:
                    data = json.loads(msg)
                    if isinstance(data, dict):
                        for key in ["lamin", "lomin", "lamax", "lomax", "ship_type", "search"]:
                            if key in data:
                                filters[key] = data[key]
                        filter_updated_event.set()
                except Exception:
                    pass
        except WebSocketDisconnect:
            pass

    async def stream_live_data():
        while True:
            try:
                ships = vessel_cache_manager.get_ships(
                    lamin=filters.get("lamin"),
                    lomin=filters.get("lomin"),
                    lamax=filters.get("lamax"),
                    lomax=filters.get("lomax"),
                    ship_type=filters.get("ship_type"),
                    search=filters.get("search"),
                )

                payload = ShipListResponse(
                    total=len(vessel_cache_manager._ships),
                    count=len(ships),
                    time=int(time.time()),
                    ships=ships,
                    live_stream_connected=aisstream_service.is_connected,
                    cached=True,
                )

                await websocket.send_text(payload.model_dump_json())
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket client streaming error: {e}")
                break

            filter_updated_event.clear()
            try:
                # Stream updates every 3 seconds or immediately when client moves bbox / changes filter
                await asyncio.wait_for(filter_updated_event.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                pass

    listener_task = asyncio.create_task(listen_for_client_messages())
    streamer_task = asyncio.create_task(stream_live_data())

    try:
        done, pending = await asyncio.wait(
            [listener_task, streamer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        manager.disconnect(websocket)
