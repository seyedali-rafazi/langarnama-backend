import json
import os
from pathlib import Path
from typing import List, Optional
from ..core.logging import logger
from ..schemas.port import Port
from ..schemas.station import CoastalStation


class ReferenceDataService:
    def __init__(self):
        self._ports: List[Port] = []
        self._stations: List[CoastalStation] = []
        self._load_reference_data()

    def _find_data_file(self, filename: str) -> Optional[Path]:
        candidates = [
            Path(__file__).resolve().parent.parent / "data" / filename,
            Path.cwd() / "backend" / "app" / "data" / filename,
            Path.cwd() / "app" / "data" / filename,
            Path.cwd() / "src" / "pages" / "Home" / "components" / "PortLayer" / "data" / filename,
            Path.cwd() / "src" / "pages" / "Home" / "components" / "StationLayer" / "data" / filename,
        ]
        for p in candidates:
            if p.exists() and p.is_file():
                return p
        return None

    def _load_reference_data(self):
        # Load Ports
        ports_path = self._find_data_file("iran_ports.json")
        if ports_path:
            try:
                with open(ports_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    self._ports = [Port(**item) for item in raw]
                    logger.info(f"Loaded {len(self._ports)} ports from {ports_path.name}")
            except Exception as e:
                logger.error(f"Failed to load ports from {ports_path}: {e}")

        if not self._ports:
            # Fallback default ports
            self._ports = [
                Port(id="PT001", name="Shahid Rajaee Port", locode="IRBND", lat=27.1, lon=56.06, city="Bandar Abbas", country="Iran", berths=40, maxDraft_m=16.5),
                Port(id="PT002", name="Bushehr Port", locode="IRBUZ", lat=28.97, lon=50.84, city="Bushehr", country="Iran", berths=14, maxDraft_m=9.5),
                Port(id="PT003", name="Bandar Imam Khomeini", locode="IRBKM", lat=30.43, lon=49.08, city="Bandar Imam Khomeini", country="Iran", berths=38, maxDraft_m=12.5),
                Port(id="PT004", name="Kharg Island Oil Terminal", locode="IRKHK", lat=29.25, lon=50.33, city="Kharg Island", country="Iran", berths=10, maxDraft_m=22.0),
                Port(id="PT005", name="Assaluyeh / Pars Port", locode="IRASA", lat=27.47, lon=52.61, city="Assaluyeh", country="Iran", berths=18, maxDraft_m=14.0),
                Port(id="PT008", name="Chabahar Shahid Beheshti", locode="IRZBR", lat=25.3, lon=60.62, city="Chabahar", country="Iran", berths=10, maxDraft_m=16.0),
            ]

        # Load Stations
        stations_path = self._find_data_file("iran_coastal_stations.json")
        if stations_path:
            try:
                with open(stations_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    self._stations = [CoastalStation(**item) for item in raw]
                    logger.info(f"Loaded {len(self._stations)} coastal stations from {stations_path.name}")
            except Exception as e:
                logger.error(f"Failed to load stations from {stations_path}: {e}")

        if not self._stations:
            # Fallback default stations
            self._stations = [
                CoastalStation(id="CS001", name="Hormuz VTS Center", type="VTS", lat=27.06, lon=56.46, frequency="VHF Ch 10", range_nm=48.0, operator="PMO", status="active"),
                CoastalStation(id="CS002", name="Bandar Abbas AIS Base", type="AIS Base", lat=27.18, lon=56.21, frequency="161.975 MHz", range_nm=60.0, operator="PMO", status="active"),
                CoastalStation(id="CS004", name="Bushehr VTS", type="VTS", lat=28.91, lon=50.83, frequency="VHF Ch 12", range_nm=40.0, operator="PMO", status="active"),
                CoastalStation(id="CS006", name="Chabahar AIS Base", type="AIS Base", lat=25.29, lon=60.6, frequency="162.025 MHz", range_nm=60.0, operator="PMO", status="active"),
            ]

    def get_ports(self) -> List[Port]:
        return self._ports

    def get_port_by_id_or_locode(self, query: str) -> Optional[Port]:
        q = query.strip().upper()
        for p in self._ports:
            if p.id.upper() == q or p.locode.upper() == q or p.name.upper() == q:
                return p
        return None

    def get_stations(self) -> List[CoastalStation]:
        return self._stations

    def get_station_by_id(self, station_id: str) -> Optional[CoastalStation]:
        sid = station_id.strip().upper()
        for s in self._stations:
            if s.id.upper() == sid or s.name.upper() == sid:
                return s
        return None


reference_data_service = ReferenceDataService()
