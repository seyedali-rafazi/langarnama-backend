from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AISMetaData(BaseModel):
    MMSI: Optional[int] = None
    MMSI_String: Optional[Any] = None
    ShipName: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    time_utc: Optional[str] = None


class AISPositionReport(BaseModel):
    Cog: Optional[float] = None
    Latitude: Optional[float] = None
    Longitude: Optional[float] = None
    MessageID: Optional[int] = None
    NavigationalStatus: Optional[int] = None
    PositionAccuracy: Optional[bool] = None
    RateOfTurn: Optional[float] = None
    Sog: Optional[float] = None
    TrueHeading: Optional[float] = None
    UserID: Optional[int] = None
    Valid: Optional[bool] = None


class AISStandardClassBPositionReport(BaseModel):
    Cog: Optional[float] = None
    Latitude: Optional[float] = None
    Longitude: Optional[float] = None
    MessageID: Optional[int] = None
    Sog: Optional[float] = None
    TrueHeading: Optional[float] = None
    UserID: Optional[int] = None
    Valid: Optional[bool] = None


class AISDimension(BaseModel):
    A: Optional[int] = None
    B: Optional[int] = None
    C: Optional[int] = None
    D: Optional[int] = None


class AISEta(BaseModel):
    Day: Optional[int] = None
    Hour: Optional[int] = None
    Minute: Optional[int] = None
    Month: Optional[int] = None


class AISShipStaticData(BaseModel):
    CallSign: Optional[str] = None
    Destination: Optional[str] = None
    Dimension: Optional[AISDimension] = None
    Draught: Optional[float] = None
    MaximumStaticDraught: Optional[float] = None
    Eta: Optional[AISEta] = None
    ImoNumber: Optional[int] = None
    MessageID: Optional[int] = None
    Name: Optional[str] = None
    Type: Optional[int] = None
    UserID: Optional[int] = None
    Valid: Optional[bool] = None


class AISMessageBody(BaseModel):
    PositionReport: Optional[AISPositionReport] = None
    StandardClassBPositionReport: Optional[AISStandardClassBPositionReport] = None
    ShipStaticData: Optional[AISShipStaticData] = None
    ExtendedClassBPositionReport: Optional[Dict[str, Any]] = None


class AISStreamMessage(BaseModel):
    MessageType: Optional[str] = None
    MetaData: Optional[AISMetaData] = None
    Message: Optional[AISMessageBody] = None
