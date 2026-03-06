# backend/app/api/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.cache_service import cache_service
import asyncio

router = APIRouter()

@router.websocket("/jobs/{job_id}/stream")
async def job_stream(websocket: WebSocket, job_id: str):
    await websocket.accept()
    
    # Ideally, we subscribe to redis events. 
    # For now, let's setup a loop on cache_service or a simulated event watcher.
    try:
        if hasattr(cache_service, "subscribe_progress"):
            async for event in cache_service.subscribe_progress(job_id):
                await websocket.send_json(event)
                if event.get("status") in ("completed", "failed"):
                    break
        else:
            # Fallback if subscribe_progress is not natively implemented yet
            # Simulated progress updates
            await websocket.send_json({"status": "queued"})
            await asyncio.sleep(1)
            for status in ['ingesting', 'parsing', 'interpreting', 'transforming', 'validating', 'rendering', 'completed']:
                await websocket.send_json({"status": status, "progress": 10})
                await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass
    finally:
        pass # The router handles closing implicitly, or we explicitly close
        try:
            await websocket.close()
        except RuntimeError:
            pass # Already closed
