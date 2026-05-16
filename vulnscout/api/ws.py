from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

_active_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/v1/scans/{scan_id}/progress")
async def scan_progress(websocket: WebSocket, scan_id: str):
    await websocket.accept()
    if scan_id not in _active_connections:
        _active_connections[scan_id] = []
    _active_connections[scan_id].append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if scan_id in _active_connections:
            _active_connections[scan_id].remove(websocket)


async def broadcast_progress(scan_id: str, data: dict):
    """Broadcast progress data to all connected clients."""
    if scan_id not in _active_connections:
        return
    dead = []
    for ws in _active_connections[scan_id]:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _active_connections[scan_id].remove(ws)
