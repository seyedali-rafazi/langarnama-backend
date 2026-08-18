import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.vessel_cache_manager import vessel_cache_manager


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["provider"] == "aisstream.io"
        assert "endpoints" in data
        assert "ships" in data["endpoints"]
        assert "ports" in data["endpoints"]
        assert "stations" in data["endpoints"]


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["provider"] == "aisstream.io"
        assert "total_cached_vessels" in data
        assert data["aisstream_configured"] is True


@pytest.mark.asyncio
async def test_stream_status_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ships/stream/status")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        assert "stream_url" in data
        assert "total_cached_vessels" in data


@pytest.mark.asyncio
async def test_list_ships():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ships")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "ships" in data
        assert data["total"] > 0
        assert len(data["ships"]) > 0

        # Check first vessel structure
        first_ship = data["ships"][0]
        assert "id" in first_ship
        assert "name" in first_ship
        assert "mmsi" in first_ship
        assert "shipType" in first_ship
        assert "lat" in first_ship
        assert "lon" in first_ship
        assert "speed_kts" in first_ship
        assert "heading_deg" in first_ship


@pytest.mark.asyncio
async def test_ship_filters():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Filter by type tanker
        response = await client.get("/api/v1/ships?ship_type=tanker")
        assert response.status_code == 200
        data = response.json()
        for ship in data["ships"]:
            assert ship["shipType"] == "tanker"

        # Filter by bounding box
        response_bbox = await client.get("/api/v1/ships?lamin=25.0&lomin=50.0&lamax=30.0&lomax=60.0")
        assert response_bbox.status_code == 200
        data_bbox = response_bbox.json()
        for ship in data_bbox["ships"]:
            assert 25.0 <= ship["lat"] <= 30.0
            assert 50.0 <= ship["lon"] <= 60.0


@pytest.mark.asyncio
async def test_ship_detail_and_track():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get list first
        list_res = await client.get("/api/v1/ships")
        ships = list_res.json()["ships"]
        if ships:
            ship_id = ships[0]["id"]
            detail_res = await client.get(f"/api/v1/ships/{ship_id}")
            assert detail_res.status_code == 200
            detail = detail_res.json()
            assert detail["id"] == ship_id

            track_res = await client.get(f"/api/v1/ships/{ship_id}/track")
            assert track_res.status_code == 200
            track = track_res.json()
            assert "points" in track


@pytest.mark.asyncio
async def test_ports_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ports")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        assert len(data["ports"]) > 0

        # Port detail lookup
        first_port = data["ports"][0]
        port_res = await client.get(f"/api/v1/ports/{first_port['id']}")
        assert port_res.status_code == 200
        assert port_res.json()["id"] == first_port["id"]


@pytest.mark.asyncio
async def test_stations_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/stations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        assert len(data["stations"]) > 0

        first_st = data["stations"][0]
        st_res = await client.get(f"/api/v1/stations/{first_st['id']}")
        assert st_res.status_code == 200
        assert st_res.json()["id"] == first_st["id"]


@pytest.mark.asyncio
async def test_stats_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_ships" in data
        assert "active_underway" in data
        assert "by_type" in data
        assert "total_ports" in data
        assert "total_stations" in data


def test_vessel_cache_upsert_logic():
    # Test position report upsert
    test_mmsi = "999888777"
    ship = vessel_cache_manager.upsert_position_report(
        mmsi=test_mmsi,
        lat=26.5,
        lon=54.2,
        speed_kts=14.5,
        heading_deg=220,
        ship_name="TEST STAR",
    )
    assert ship.mmsi == test_mmsi
    assert ship.lat == 26.5
    assert ship.lon == 54.2
    assert ship.speed_kts == 14.5
    assert ship.heading_deg == 220
    assert len(ship.path) >= 1

    # Test static data upsert (e.g. Tanker type code 80)
    static_ship = vessel_cache_manager.upsert_static_data(
        mmsi=test_mmsi,
        name="TEST STAR OIL",
        callsign="EPTS",
        imo=9876543,
        type_code=80,
        draught=12.5,
        destination="BANDAR ABBAS",
    )
    assert static_ship is not None
    assert static_ship.name == "TEST STAR OIL"
    assert static_ship.shipType == "tanker"
    assert static_ship.callsign == "EPTS"
    assert static_ship.imo == 9876543
    assert static_ship.draft_m == 12.5
    assert static_ship.destination_port == "BANDAR ABBAS"
