from typing import Dict, Optional
from pydantic import BaseModel, Field


class StatsResponse(BaseModel):
    total_ships: int = Field(description="Total registered vessels")
    active_underway: int = Field(description="Vessels moving with speed >= 0.5 kn")
    anchored_moored: int = Field(description="Vessels stationary / anchored (< 0.5 kn)")
    avg_speed_kts: float = Field(description="Average speed of active vessels")
    by_type: Dict[str, int] = Field(description="Counts breakdown per vessel type")
    total_ports: int = Field(description="Number of monitored ports")
    total_stations: int = Field(description="Number of coastal AIS/VTS stations")
    aisstream_connected: bool = Field(description="AISStream WebSocket connection status")
    messages_received: int = Field(description="Total AIS messages processed since startup")
    last_message_time: Optional[str] = Field(default=None, description="Timestamp of latest AIS message")
    uptime_seconds: float = Field(description="Backend server uptime in seconds")
