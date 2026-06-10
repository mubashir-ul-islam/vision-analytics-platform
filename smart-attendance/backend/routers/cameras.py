import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from services.camera_worker import get_camera_state

router = APIRouter(prefix="/camera", tags=["cameras"])


async def _mjpeg_generator(camera_type: str):
    state = get_camera_state(camera_type)
    try:
        while True:
            frame = state.latest_frame
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            await asyncio.sleep(0.033)
    except asyncio.CancelledError:
        pass


@router.get("/entry/stream")
async def entry_stream():
    return StreamingResponse(
        _mjpeg_generator("entrance"),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/exit/stream")
async def exit_stream():
    return StreamingResponse(
        _mjpeg_generator("exit"),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/entry/snapshot")
async def entry_snapshot():
    frame = get_camera_state("entrance").latest_frame
    if not frame:
        raise HTTPException(status_code=503, detail="Camera not ready")
    return Response(content=frame, media_type="image/jpeg")


@router.get("/exit/snapshot")
async def exit_snapshot():
    frame = get_camera_state("exit").latest_frame
    if not frame:
        raise HTTPException(status_code=503, detail="Camera not ready")
    return Response(content=frame, media_type="image/jpeg")
