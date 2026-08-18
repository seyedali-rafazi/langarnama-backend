import asyncio
import json
import time
from typing import Any, Dict, Optional
import websockets

from ..core.config import settings
from ..core.logging import logger
from .vessel_cache_manager import vessel_cache_manager


class AISStreamService:
    """
    Continuous background service managing the WebSocket connection to aisstream.io,
    parsing incoming real-time AIS messages, and updating the vessel registry.
    """

    def __init__(self):
        self._running = False
        self._connected = False
        self._task: Optional[asyncio.Task] = None
        self._last_connected_at: Optional[float] = None
        self._total_messages_received: int = 0
        self._last_error: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "connected": self._connected,
            "api_key_configured": bool(settings.AISSTREAM_API_KEY),
            "stream_url": settings.AISSTREAM_WS_URL,
            "bounding_boxes": settings.AISSTREAM_BBOX,
            "messages_received": self._total_messages_received,
            "last_connected_epoch": self._last_connected_at,
            "last_error": self._last_error,
        }

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="aisstream_worker")
        logger.info("AISStream background ingestion service started.")

    async def stop(self):
        self._running = False
        self._connected = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AISStream background ingestion service stopped.")

    async def _run_loop(self):
        if not settings.AISSTREAM_API_KEY:
            logger.warning("AISSTREAM_API_KEY not configured. Running with baseline/simulated data only.")
            return

        reconnect_delay = settings.AISSTREAM_RECONNECT_DELAY_SECONDS

        while self._running:
            try:
                logger.info(f"Connecting to AISStream.io at {settings.AISSTREAM_WS_URL}...")
                async with websockets.connect(
                    settings.AISSTREAM_WS_URL,
                    ping_interval=20,
                    ping_timeout=15,
                    close_timeout=10,
                ) as ws:
                    self._connected = True
                    self._last_connected_at = time.time()
                    self._last_error = None
                    reconnect_delay = settings.AISSTREAM_RECONNECT_DELAY_SECONDS
                    logger.info("Successfully connected to AISStream.io. Sending subscription payload...")

                    # Send AISStream subscription message
                    subscription_msg = {
                        "APIKey": settings.AISSTREAM_API_KEY,
                        "BoundingBoxes": settings.AISSTREAM_BBOX,
                        "FilterMessageTypes": settings.AISSTREAM_MESSAGE_TYPES,
                    }
                    await ws.send(json.dumps(subscription_msg))
                    logger.info("AISStream subscription registered. Listening for AIS messages...")

                    async for message_str in ws:
                        if not self._running:
                            break
                        self._process_message(message_str)

            except asyncio.CancelledError:
                self._connected = False
                break
            except Exception as e:
                self._connected = False
                self._last_error = str(e)
                logger.warning(f"AISStream WebSocket error: {e}. Reconnecting in {reconnect_delay:.1f}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, 60.0)

    def _process_message(self, message_str: str):
        try:
            data = json.loads(message_str)
            if not isinstance(data, dict):
                return

            self._total_messages_received += 1
            msg_type = data.get("MessageType")
            meta = data.get("MetaData", {})
            mmsi = str(meta.get("MMSI") or meta.get("MMSI_String") or "").strip()
            if not mmsi:
                return

            time_utc = meta.get("time_utc")
            ship_name = meta.get("ShipName")
            msg_body = data.get("Message", {})

            if msg_type == "PositionReport":
                pos = msg_body.get("PositionReport", {})
                lat = pos.get("Latitude") if pos.get("Latitude") is not None else meta.get("latitude")
                lon = pos.get("Longitude") if pos.get("Longitude") is not None else meta.get("longitude")
                if lat is not None and lon is not None:
                    # Filter out invalid 91.0 / 181.0 null GPS coords
                    if abs(lat) <= 90.0 and abs(lon) <= 180.0 and not (abs(lat) < 0.001 and abs(lon) < 0.001):
                        vessel_cache_manager.upsert_position_report(
                            mmsi=mmsi,
                            lat=float(lat),
                            lon=float(lon),
                            speed_kts=pos.get("Sog"),
                            heading_deg=pos.get("TrueHeading"),
                            cog=pos.get("Cog"),
                            rot=pos.get("RateOfTurn"),
                            nav_status=str(pos.get("NavigationalStatus")) if pos.get("NavigationalStatus") is not None else None,
                            ship_name=ship_name,
                            time_utc=time_utc,
                        )

            elif msg_type == "StandardClassBPositionReport":
                pos = msg_body.get("StandardClassBPositionReport", {})
                lat = pos.get("Latitude") if pos.get("Latitude") is not None else meta.get("latitude")
                lon = pos.get("Longitude") if pos.get("Longitude") is not None else meta.get("longitude")
                if lat is not None and lon is not None:
                    if abs(lat) <= 90.0 and abs(lon) <= 180.0 and not (abs(lat) < 0.001 and abs(lon) < 0.001):
                        vessel_cache_manager.upsert_position_report(
                            mmsi=mmsi,
                            lat=float(lat),
                            lon=float(lon),
                            speed_kts=pos.get("Sog"),
                            heading_deg=pos.get("TrueHeading"),
                            cog=pos.get("Cog"),
                            ship_name=ship_name,
                            time_utc=time_utc,
                        )

            elif msg_type == "ExtendedClassBPositionReport":
                pos = msg_body.get("ExtendedClassBPositionReport", {})
                lat = pos.get("Latitude") if pos.get("Latitude") is not None else meta.get("latitude")
                lon = pos.get("Longitude") if pos.get("Longitude") is not None else meta.get("longitude")
                raw_name = pos.get("Name") or ship_name
                name = str(raw_name).strip() if raw_name else None
                type_code = pos.get("Type") or pos.get("ShipType")
                dimension = pos.get("Dimension")

                if lat is not None and lon is not None:
                    if abs(lat) <= 90.0 and abs(lon) <= 180.0 and not (abs(lat) < 0.001 and abs(lon) < 0.001):
                        vessel_cache_manager.upsert_position_report(
                            mmsi=mmsi,
                            lat=float(lat),
                            lon=float(lon),
                            speed_kts=pos.get("Sog"),
                            heading_deg=pos.get("TrueHeading"),
                            cog=pos.get("Cog"),
                            ship_name=name,
                            time_utc=time_utc,
                        )
                if name or type_code or dimension:
                    vessel_cache_manager.upsert_static_data(
                        mmsi=mmsi,
                        name=name,
                        type_code=type_code,
                        dimension=dimension,
                        time_utc=time_utc,
                    )

            elif msg_type == "ShipStaticData":
                static = msg_body.get("ShipStaticData", {})
                raw_name = static.get("Name") or ship_name
                name = str(raw_name).strip() if raw_name else None
                callsign = str(static.get("CallSign")).strip() if static.get("CallSign") else None
                imo = static.get("ImoNumber")
                type_code = static.get("Type")
                dimension = static.get("Dimension")
                draught = static.get("MaximumStaticDraught") or static.get("Draught")
                destination = str(static.get("Destination")).strip() if static.get("Destination") else None

                eta_obj = static.get("Eta")
                eta_str = None
                if isinstance(eta_obj, dict):
                    month = eta_obj.get("Month")
                    day = eta_obj.get("Day")
                    hour = eta_obj.get("Hour")
                    minute = eta_obj.get("Minute")
                    if month and day:
                        eta_str = f"{month:02d}-{day:02d} {hour or 0:02d}:{minute or 0:02d} UTC"

                vessel_cache_manager.upsert_static_data(
                    mmsi=mmsi,
                    name=name,
                    callsign=callsign,
                    imo=imo,
                    type_code=type_code,
                    dimension=dimension,
                    draught=draught,
                    destination=destination,
                    eta_str=eta_str,
                    time_utc=time_utc,
                )

        except Exception as e:
            logger.debug(f"Error parsing AIS message: {e}")


aisstream_service = AISStreamService()
