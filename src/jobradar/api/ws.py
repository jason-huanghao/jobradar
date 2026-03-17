"""WebSocket endpoint — streams pipeline progress events to the browser."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..pipeline import JobRadarPipeline, PipelineProgress
from .main import get_config

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/pipeline")
async def pipeline_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if msg.get("action") == "run":
                await _run_pipeline(websocket, msg.get("mode", "full"))
            else:
                await _send(websocket, "error", message=f"Unknown action: {msg.get('action')}")
    except WebSocketDisconnect:
        logger.info("WS client disconnected")
    except Exception as exc:
        logger.error("WS error: %s", exc)


async def _run_pipeline(ws: WebSocket, mode: str):
    cfg = get_config()
    queue: asyncio.Queue[PipelineProgress | None] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def on_progress(event: PipelineProgress):
        loop.call_soon_threadsafe(queue.put_nowait, event)

    # Run pipeline in thread pool so it doesn't block the event loop
    async def run_in_thread():
        try:
            pipeline = JobRadarPipeline(cfg)
            await loop.run_in_executor(None, lambda: pipeline.run(mode=mode, on_progress=on_progress))
        except Exception as exc:
            queue.put_nowait(PipelineProgress(event="error", data={"message": str(exc)}))
        finally:
            queue.put_nowait(None)  # sentinel

    # Start pipeline thread
    task = asyncio.create_task(run_in_thread())

    # Drain queue and forward to client
    while True:
        item = await queue.get()
        if item is None:
            break
        await _send(ws, item.event, **item.data)

    await task  # ensure thread cleanup


async def _send(ws: WebSocket, event: str, **data: Any):
    try:
        await ws.send_text(json.dumps({"event": event, "data": data}))
    except Exception:
        pass
