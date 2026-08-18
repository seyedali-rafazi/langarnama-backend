import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[
            str(BASE_DIR / ".env"),
            str(BASE_DIR.parent / ".env"),
            ".env",
            "backend/.env",
        ],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    APP_NAME: str = "Langarnama Vessel Tracking API"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # AISStream.io Configuration (https://aisstream.io)
    AISSTREAM_API_KEY: Optional[str] = Field(
        default="4e9ffc8e2f1a92a58fc18d98651ad789d3a80501",
        validation_alias=AliasChoices("AISSTREAM_API_KEY", "api_key", "AIS_KEY")
    )
    AISSTREAM_WS_URL: str = "wss://stream.aisstream.io/v0/stream"
    AISSTREAM_RECONNECT_DELAY_SECONDS: float = 5.0
    AISSTREAM_CONNECT_TIMEOUT_SECONDS: float = 15.0

    # Default Bounding Box Filter for AISStream (latitude, longitude)
    # Persian Gulf, Gulf of Oman, Arabian Sea & Caspian Sea region
    AISSTREAM_BBOX: List[List[List[float]]] = [[[22.0, 47.0], [40.0, 64.0]]]
    AISSTREAM_MESSAGE_TYPES: List[str] = [
        "PositionReport",
        "StandardClassBPositionReport",
        "ShipStaticData",
        "ExtendedClassBPositionReport",
    ]

    # In-Memory Cache & Track Limits
    SHIP_INACTIVE_TIMEOUT_SECONDS: int = 3600
    MAX_TRACK_POINTS_PER_SHIP: int = 100
    FALLBACK_SAMPLE_DATA: bool = True

    # Default Bounding Box for queries
    DEFAULT_LAMIN: Optional[float] = 22.0
    DEFAULT_LOMIN: Optional[float] = 47.0
    DEFAULT_LAMAX: Optional[float] = 40.0
    DEFAULT_LOMAX: Optional[float] = 64.0

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://www.langarnama.ir",
    ]


settings = Settings()
