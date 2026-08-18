# Langarnama Backend - AISStream.io Marine Vessel Tracking API

High-performance, async **FastAPI** backend that ingests, enriches, caches, and serves real-time maritime AIS (Automatic Identification System) vessel telemetry, wakes/tracks, ports, and coastal stations powered by **AISStream.io**.

---

## Features

- 🚢 **Live AISStream Ingestion**: Continuous WebSocket connection (`wss://stream.aisstream.io/v0/stream`) streaming real-time position reports and static vessel data.
- ⚡ **Zero-Latency In-Memory Cache**: High-speed spatial indexing and trajectory tracking without requiring a heavy SQL database.
- 🛡️ **Offline & Resilient Guard**: Pre-seeded with rich baseline Iranian and Middle Eastern fleet data (`iran_ships.json`), plus automatic reconnection with exponential backoff.
- 🎯 **Domain-Enriched Telemetry**: Automatically categorizes vessel types (Tanker, Cargo, Fishing, Passenger, Tug, Military), calculates speeds, headings, dimensions, and wake breadcrumbs.
- 🌐 **Interactive Documentation**: Built-in interactive Swagger UI (`/docs`) and ReDoc (`/redoc`).
- 🔄 **Real-Time Client WebSocket**: Live WebSocket endpoint (`/api/v1/ws/live`) with dynamic client bounding-box filtering for Mapbox/Deck.GL clients.
- 📍 **Spatial & Attribute Filtering**: Full support for bounding box coordinates (`lamin`, `lomin`, `lamax`, `lomax`), MMSI, callsign, vessel name, operator, and speed ranges.

---

## Quick Start

### 1. Requirements

- Python 3.10+ (tested with Python 3.14)
- Pip

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Your `.env` comes preconfigured with the AISStream API key:

```env
AISSTREAM_API_KEY=4e9ffc8e2f1a92a58fc18d98651ad789d3a80501
AISSTREAM_WS_URL=wss://stream.aisstream.io/v0/stream
```

### 4. Run the Server

Using the runner script:
```bash
python run.py
```

Or directly via Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: **http://localhost:8000**  
Interactive API Docs (Swagger): **http://localhost:8000/docs**  
ReDoc API Docs: **http://localhost:8000/redoc**  

---

## API Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root information and available endpoint routes |
| `GET` | `/health` | Health check & AISStream connection status |
| `GET` | `/api/v1/ships` | List active vessels with filters (bbox, search, ship_type, speed) |
| `GET` | `/api/v1/ships/{id}` | Detailed telemetry and dimensions for a single vessel |
| `GET` | `/api/v1/ships/{id}/track` | Trajectory waypoints / wake history for a specific vessel |
| `GET` | `/api/v1/ships/stream/status` | AISStream connection status and message metrics |
| `GET` | `/api/v1/ports` | Major commercial ports and terminals database |
| `GET` | `/api/v1/ports/{code_or_id}` | Port detail by UN/LOCODE or ID |
| `GET` | `/api/v1/stations` | Coastal AIS receivers, VTS centers, and lighthouses |
| `GET` | `/api/v1/stations/{id}` | Coastal station detail |
| `GET` | `/api/v1/stats` | Active fleet metrics (total vessels, underway vs anchored, type breakdown) |
| `WS`  | `/api/v1/ws/live` | WebSocket real-time live vessel streaming for frontend map |

---

## Running Tests

Run the test suite with `pytest`:

```bash
python -m pytest tests -v
```
