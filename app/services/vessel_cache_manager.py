import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..core.config import settings
from ..core.logging import logger
from ..schemas.ship import Ship, ShipDetail, ShipTrackResponse, ShipType
from ..schemas.stats import StatsResponse


class VesselCacheManager:
    """
    In-memory vessel registry managing real-time vessel states,
    historical tracks/wakes, spatial queries, and baseline reference data.
    """

    def __init__(self):
        self._ships: Dict[str, ShipDetail] = {}
        self._mmsi_to_id: Dict[str, str] = {}
        self._last_update_time: Optional[int] = None
        self._start_time: float = time.time()
        self._messages_processed: int = 0
        self._last_message_iso: Optional[str] = None
        self.ensure_baseline_loaded()

    def _find_ships_file(self) -> Optional[Path]:
        candidates = [
            Path(__file__).resolve().parent.parent / "data" / "iran_ships.json",
            Path.cwd() / "backend" / "app" / "data" / "iran_ships.json",
            Path.cwd() / "app" / "data" / "iran_ships.json",
            Path.cwd() / "src" / "pages" / "Home" / "components" / "ShipLayer" / "data" / "iran_ships.json",
        ]
        for p in candidates:
            if p.exists() and p.is_file():
                return p
        return None

    def ensure_baseline_loaded(self):
        """Loads baseline vessels from json if registry is empty."""
        if self._ships:
            return

        ships_path = self._find_ships_file()
        if ships_path:
            try:
                with open(ships_path, "r", encoding="utf-8") as f:
                    raw_ships = json.load(f)
                    for item in raw_ships:
                        ship_obj = ShipDetail(
                            id=str(item.get("id")),
                            name=str(item.get("name", "Unknown Vessel")),
                            mmsi=str(item.get("mmsi")),
                            operator=str(item.get("operator", "Independent")),
                            shipType=self._normalize_ship_type(item.get("shipType")),
                            lat=float(item.get("lat", 0.0)),
                            lon=float(item.get("lon", 0.0)),
                            heading_deg=float(item.get("heading_deg", 0.0)),
                            speed_kts=float(item.get("speed_kts", 0.0)),
                            draft_m=float(item.get("draft_m", 6.0)),
                            length_m=float(item.get("length_m", 100.0)),
                            beam_m=float(item.get("beam_m", 20.0)) if item.get("beam_m") else None,
                            origin_port=str(item.get("origin_port", "Unknown")),
                            destination_port=str(item.get("destination_port", "In Transit")),
                            path=item.get("path", []),
                            lastUpdate=str(item.get("lastUpdate", datetime.now(timezone.utc).isoformat())),
                            country=item.get("country", "Iran"),
                            is_live=False,
                        )
                        self._ships[ship_obj.id] = ship_obj
                        self._mmsi_to_id[ship_obj.mmsi] = ship_obj.id

                    self._last_update_time = int(time.time())
                    logger.info(f"Loaded {len(self._ships)} baseline vessels from {ships_path.name}")
            except Exception as e:
                logger.error(f"Failed to load baseline ships from {ships_path}: {e}")

    @staticmethod
    def _normalize_ship_type(raw_type: Any) -> ShipType:
        if not raw_type:
            return "cargo"
        t = str(raw_type).strip().lower()
        if t in ["tanker", "oil tanker", "lng", "lpg"]:
            return "tanker"
        if t in ["fishing", "trawler", "dhow"]:
            return "fishing"
        if t in ["passenger", "ferry", "cruise"]:
            return "passenger"
        if t in ["tug", "support", "towing", "dredger"]:
            return "tug"
        if t in ["military", "naval", "patrol", "coast guard", "law enforcement"]:
            return "military"
        if t in ["cargo", "container", "bulk", "bulk carrier", "general cargo"]:
            return "cargo"
        return "cargo"

    @staticmethod
    def map_ais_type_code_to_ship_type(type_code: Optional[int]) -> ShipType:
        """
        Maps standard ITU-R M.1371 / AIS vessel type codes to system ShipType:
        30-32: Fishing
        35: Military ops / law enforcement
        52: Tug / Towing
        60-69: Passenger
        70-79: Cargo
        80-89: Tanker
        50-59: Special craft / Port tenders
        """
        if type_code is None:
            return "cargo"

        code = int(type_code)
        if code in [30, 31, 32]:
            return "fishing"
        if code == 35 or code == 55:
            return "military"
        if code in [52, 31, 32]:
            return "tug"
        if 60 <= code <= 69:
            return "passenger"
        if 70 <= code <= 79:
            return "cargo"
        if 80 <= code <= 89:
            return "tanker"
        if 50 <= code <= 59:
            return "tug"

        return "cargo"

    def record_message_processed(self, timestamp_iso: Optional[str] = None):
        self._messages_processed += 1
        self._last_message_iso = timestamp_iso or datetime.now(timezone.utc).isoformat()
        self._last_update_time = int(time.time())

    def upsert_position_report(
        self,
        mmsi: str,
        lat: float,
        lon: float,
        speed_kts: Optional[float] = None,
        heading_deg: Optional[float] = None,
        cog: Optional[float] = None,
        rot: Optional[float] = None,
        nav_status: Optional[str] = None,
        ship_name: Optional[str] = None,
        time_utc: Optional[str] = None,
    ) -> ShipDetail:
        """
        Updates an existing vessel or inserts a new one from AIS Position Report.
        """
        self.record_message_processed(time_utc)
        mmsi_str = str(mmsi).strip()
        timestamp = time_utc or datetime.now(timezone.utc).isoformat()
        ship_id = self._mmsi_to_id.get(mmsi_str) or f"SH_{mmsi_str}"

        # Clamp heading and speed
        hdg = heading_deg if (heading_deg is not None and 0 <= heading_deg <= 360) else (cog or 0.0)
        spd = max(0.0, speed_kts if speed_kts is not None else 0.0)

        existing = self._ships.get(ship_id)
        if existing:
            # Check if vessel has moved to add waypoint
            path = list(existing.path)
            if not path or (abs(path[-1][0] - lat) > 0.0001 or abs(path[-1][1] - lon) > 0.0001):
                path.append([lat, lon])
                if len(path) > settings.MAX_TRACK_POINTS_PER_SHIP:
                    path.pop(0)

            updated = existing.model_copy(
                update={
                    "lat": lat,
                    "lon": lon,
                    "heading_deg": hdg,
                    "speed_kts": spd,
                    "cog": cog if cog is not None else existing.cog,
                    "rot": rot if rot is not None else existing.rot,
                    "nav_status": nav_status if nav_status is not None else existing.nav_status,
                    "name": ship_name if (ship_name and not existing.name) else existing.name,
                    "path": path,
                    "lastUpdate": timestamp,
                    "is_live": True,
                }
            )
            self._ships[ship_id] = updated
            return updated
        else:
            # Create new vessel
            name = (ship_name or f"MMSI {mmsi_str}").strip()
            new_ship = ShipDetail(
                id=ship_id,
                name=name,
                mmsi=mmsi_str,
                operator="AIS Stream Vessel",
                shipType="cargo",
                lat=lat,
                lon=lon,
                heading_deg=hdg,
                speed_kts=spd,
                cog=cog,
                rot=rot,
                nav_status=nav_status,
                draft_m=7.5,
                length_m=120.0,
                origin_port="Unknown",
                destination_port="In Transit",
                path=[[lat, lon]],
                lastUpdate=timestamp,
                country="International",
                is_live=True,
            )
            self._ships[ship_id] = new_ship
            self._mmsi_to_id[mmsi_str] = ship_id
            return new_ship

    def upsert_static_data(
        self,
        mmsi: str,
        name: Optional[str] = None,
        callsign: Optional[str] = None,
        imo: Optional[int] = None,
        type_code: Optional[int] = None,
        dimension: Optional[Dict[str, Any]] = None,
        draught: Optional[float] = None,
        destination: Optional[str] = None,
        eta_str: Optional[str] = None,
        time_utc: Optional[str] = None,
    ) -> Optional[ShipDetail]:
        """
        Updates static vessel metadata (name, callsign, IMO, dimensions, destination, ETA).
        """
        self.record_message_processed(time_utc)
        mmsi_str = str(mmsi).strip()
        timestamp = time_utc or datetime.now(timezone.utc).isoformat()
        ship_id = self._mmsi_to_id.get(mmsi_str) or f"SH_{mmsi_str}"

        # Dimensions length and beam calculation
        length_m = None
        beam_m = None
        dim_a = dim_b = dim_c = dim_d = None
        if dimension:
            dim_a = dimension.get("A", 0) or 0
            dim_b = dimension.get("B", 0) or 0
            dim_c = dimension.get("C", 0) or 0
            dim_d = dimension.get("D", 0) or 0
            if (dim_a + dim_b) > 0:
                length_m = float(dim_a + dim_b)
            if (dim_c + dim_d) > 0:
                beam_m = float(dim_c + dim_d)

        ship_type = self.map_ais_type_code_to_ship_type(type_code) if type_code is not None else None

        existing = self._ships.get(ship_id)
        if existing:
            updates: Dict[str, Any] = {"lastUpdate": timestamp, "is_live": True}
            if name and name.strip() and name.strip() != "0":
                updates["name"] = name.strip()
            if callsign and callsign.strip():
                updates["callsign"] = callsign.strip()
            if imo and imo > 0:
                updates["imo"] = imo
            if ship_type:
                updates["shipType"] = ship_type
            if length_m:
                updates["length_m"] = length_m
            if beam_m:
                updates["beam_m"] = beam_m
            if draught and draught > 0:
                updates["draft_m"] = draught
            if destination and destination.strip():
                updates["destination_port"] = destination.strip()
            if eta_str:
                updates["eta"] = eta_str
            if dim_a is not None:
                updates["dimension_a"] = dim_a
                updates["dimension_b"] = dim_b
                updates["dimension_c"] = dim_c
                updates["dimension_d"] = dim_d

            updated = existing.model_copy(update=updates)
            self._ships[ship_id] = updated
            return updated
        else:
            # Insert static placeholder until position arrives
            clean_name = (name or f"MMSI {mmsi_str}").strip()
            new_ship = ShipDetail(
                id=ship_id,
                name=clean_name,
                mmsi=mmsi_str,
                operator="AIS Stream Vessel",
                shipType=ship_type or "cargo",
                lat=0.0,
                lon=0.0,
                heading_deg=0.0,
                speed_kts=0.0,
                draft_m=draught or 7.0,
                length_m=length_m or 100.0,
                beam_m=beam_m,
                callsign=callsign,
                imo=imo,
                origin_port="Unknown",
                destination_port=destination or "In Transit",
                eta=eta_str,
                path=[],
                lastUpdate=timestamp,
                is_live=True,
                dimension_a=dim_a,
                dimension_b=dim_b,
                dimension_c=dim_c,
                dimension_d=dim_d,
            )
            self._ships[ship_id] = new_ship
            self._mmsi_to_id[mmsi_str] = ship_id
            return new_ship

    def get_ships(
        self,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None,
        search: Optional[str] = None,
        ship_type: Optional[str] = None,
        operator: Optional[str] = None,
        min_speed: Optional[float] = None,
        max_speed: Optional[float] = None,
        only_live: Optional[bool] = None,
    ) -> List[Ship]:
        """
        Retrieves vessels matching bounding box, search, and classification filters.
        """
        results: List[Ship] = []
        search_lower = search.strip().lower() if search else None
        type_filter = ship_type.strip().lower() if ship_type else None
        operator_lower = operator.strip().lower() if operator else None

        for ship in self._ships.values():
            # Skip vessels without valid coordinates (lat=0, lon=0)
            if abs(ship.lat) < 0.001 and abs(ship.lon) < 0.001:
                continue

            # Bounding box filter
            if lamin is not None and ship.lat < lamin:
                continue
            if lamax is not None and ship.lat > lamax:
                continue
            if lomin is not None and ship.lon < lomin:
                continue
            if lomax is not None and ship.lon > lomax:
                continue

            # Search query filter (matches name, MMSI, callsign, IMO, destination)
            if search_lower:
                match = (
                    search_lower in ship.name.lower()
                    or search_lower in ship.mmsi.lower()
                    or (ship.callsign and search_lower in ship.callsign.lower())
                    or (ship.imo and search_lower in str(ship.imo))
                    or search_lower in ship.destination_port.lower()
                    or search_lower in ship.operator.lower()
                )
                if not match:
                    continue

            # Ship type filter
            if type_filter and type_filter != "all" and ship.shipType.lower() != type_filter:
                continue

            # Operator filter
            if operator_lower and operator_lower not in ship.operator.lower():
                continue

            # Speed filters
            if min_speed is not None and ship.speed_kts < min_speed:
                continue
            if max_speed is not None and ship.speed_kts > max_speed:
                continue

            # Live flag filter
            if only_live is not None and ship.is_live != only_live:
                continue

            # Convert ShipDetail to Ship representation
            results.append(
                Ship(
                    id=ship.id,
                    name=ship.name,
                    mmsi=ship.mmsi,
                    operator=ship.operator,
                    shipType=ship.shipType,
                    lat=ship.lat,
                    lon=ship.lon,
                    heading_deg=ship.heading_deg,
                    speed_kts=ship.speed_kts,
                    draft_m=ship.draft_m,
                    length_m=ship.length_m,
                    beam_m=ship.beam_m,
                    callsign=ship.callsign,
                    imo=ship.imo,
                    nav_status=ship.nav_status,
                    origin_port=ship.origin_port,
                    destination_port=ship.destination_port,
                    eta=ship.eta,
                    path=ship.path,
                    lastUpdate=ship.lastUpdate,
                    country=ship.country,
                    flag=ship.flag,
                )
            )

        return results

    def get_ship_detail(self, ship_id_or_mmsi: str) -> Optional[ShipDetail]:
        """Looks up vessel by either ID (e.g. SH1001) or MMSI."""
        q = str(ship_id_or_mmsi).strip()
        if q in self._ships:
            return self._ships[q]
        if q in self._mmsi_to_id:
            return self._ships.get(self._mmsi_to_id[q])
        for s in self._ships.values():
            if s.id.lower() == q.lower() or s.mmsi == q or (s.callsign and s.callsign.lower() == q.lower()):
                return s
        return None

    def get_ship_track(self, ship_id_or_mmsi: str) -> Optional[ShipTrackResponse]:
        detail = self.get_ship_detail(ship_id_or_mmsi)
        if not detail:
            return None
        return ShipTrackResponse(
            ship_id=detail.id,
            mmsi=detail.mmsi,
            name=detail.name,
            shipType=detail.shipType,
            points=detail.path,
            count=len(detail.path),
            last_update=detail.lastUpdate,
        )

    def get_stats(self, aisstream_connected: bool = False) -> StatsResponse:
        total = len(self._ships)
        underway = 0
        anchored = 0
        speed_sum = 0.0
        speed_count = 0
        by_type: Dict[str, int] = {
            "tanker": 0,
            "cargo": 0,
            "fishing": 0,
            "passenger": 0,
            "tug": 0,
            "military": 0,
        }

        for s in self._ships.values():
            if s.speed_kts >= 0.5:
                underway += 1
                speed_sum += s.speed_kts
                speed_count += 1
            else:
                anchored += 1

            st = s.shipType if s.shipType in by_type else "cargo"
            by_type[st] = by_type.get(st, 0) + 1

        avg_spd = round(speed_sum / speed_count, 1) if speed_count > 0 else 0.0

        from .reference_data_service import reference_data_service

        return StatsResponse(
            total_ships=total,
            active_underway=underway,
            anchored_moored=anchored,
            avg_speed_kts=avg_spd,
            by_type=by_type,
            total_ports=len(reference_data_service.get_ports()),
            total_stations=len(reference_data_service.get_stations()),
            aisstream_connected=aisstream_connected,
            messages_received=self._messages_processed,
            last_message_time=self._last_message_iso,
            uptime_seconds=round(time.time() - self._start_time, 1),
        )

    def get_cache_status(self, aisstream_connected: bool = False) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "provider": "aisstream.io",
            "connected": aisstream_connected,
            "total_cached_vessels": len(self._ships),
            "messages_processed": self._messages_processed,
            "last_message_time": self._last_message_iso,
            "last_update_epoch": self._last_update_time,
            "uptime_seconds": round(time.time() - self._start_time, 1),
        }


vessel_cache_manager = VesselCacheManager()
