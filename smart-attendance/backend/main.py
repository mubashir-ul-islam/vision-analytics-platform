import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import settings
from database import init_db
from routers import employees, attendance, cameras
from schemas import SystemStatus, ConfigUpdate, CameraAssignment
from services import compreface as compreface_svc
from services import camera_worker
from services.camera_worker import get_camera_state, start_workers, stop_workers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

event_queue: asyncio.Queue = asyncio.Queue()
sse_clients: list[asyncio.Queue] = []


async def event_dispatcher():
    while True:
        event = await event_queue.get()
        for client_queue in list(sse_clients):
            await client_queue.put(event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    loop = asyncio.get_running_loop()
    start_workers(event_queue, loop)
    dispatcher_task = asyncio.create_task(event_dispatcher())
    logger.info("Attendance backend started")
    yield
    stop_workers()
    dispatcher_task.cancel()
    logger.info("Attendance backend stopped")


app = FastAPI(title="Smart Attendance API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(employees.router)
app.include_router(attendance.router)
app.include_router(cameras.router)


@app.get("/api/events")
async def sse_events(request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    sse_clients.append(queue)

    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            if queue in sse_clients:
                sse_clients.remove(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/system/status", response_model=SystemStatus)
async def system_status():
    cf_ready = settings.compreface_ready and await compreface_svc.health_check()
    return SystemStatus(
        compreface_ready=cf_ready,
        compreface_url=settings.compreface_url,
        cameras={
            "entrance": get_camera_state("entrance").camera_ok,
            "exit": get_camera_state("exit").camera_ok,
        },
    )


@app.put("/api/system/config")
async def update_config(body: ConfigUpdate):
    settings.update_api_key(body.compreface_api_key)
    return {"updated": True}


@app.get("/api/system/cameras")
async def list_cameras():
    loop = asyncio.get_running_loop()
    available = await loop.run_in_executor(None, camera_worker.list_available_cameras)
    return {
        "available": available,
        "current": {
            "entrance": settings.entrance_camera_source,
            "exit": settings.exit_camera_source,
        },
    }


@app.put("/api/system/cameras")
async def set_cameras(body: CameraAssignment):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, camera_worker.restart_workers, body.entrance_source, body.exit_source
    )
    return {"updated": True}


@app.get("/health")
def health():
    return {"status": "ok"}
