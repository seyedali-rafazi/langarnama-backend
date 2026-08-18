from typing import Optional
from fastapi import APIRouter, HTTPException

from ....schemas.port import Port, PortListResponse
from ....services.reference_data_service import reference_data_service

router = APIRouter(prefix="/ports", tags=["Ports"])


@router.get("", response_model=PortListResponse)
async def list_ports():
    """
    Returns reference list of major commercial maritime ports, terminals, and docks.
    """
    ports = reference_data_service.get_ports()
    return PortListResponse(total=len(ports), ports=ports)


@router.get("/{code_or_id}", response_model=Port)
async def get_port(code_or_id: str):
    """
    Retrieves port details by UN/LOCODE (e.g. IRBND) or port ID (e.g. PT001).
    """
    port = reference_data_service.get_port_by_id_or_locode(code_or_id)
    if port:
        return port
    raise HTTPException(status_code=404, detail=f"Port '{code_or_id}' not found")
