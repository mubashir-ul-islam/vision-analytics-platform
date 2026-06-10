import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


def _async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.compreface_url,
        headers={"x-api-key": settings.compreface_api_key},
        timeout=15.0,
    )


def _sync_client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.compreface_url,
        headers={"x-api-key": settings.compreface_api_key},
        timeout=15.0,
    )


def recognize_sync(image_bytes: bytes) -> list[dict]:
    """Blocking call — for use inside camera worker threads."""
    with _sync_client() as client:
        resp = client.post(
            "/api/v1/recognition/recognize",
            files={"file": ("frame.jpg", image_bytes, "image/jpeg")},
            params={"limit": 0, "prediction_count": 1},
        )
        if resp.status_code == 400:
            try:
                body = resp.json()
            except Exception:
                body = {}
            # code 28 = no face detected in image — normal, not an error
            if body.get("code") == 28:
                return []
            logger.warning("CompreFace recognize HTTP 400: %s", body)
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json().get("result", [])


async def enroll_face(image_bytes: bytes, subject: str) -> dict:
    async with _async_client() as client:
        resp = await client.post(
            "/api/v1/recognition/faces",
            files={"file": ("photo.jpg", image_bytes, "image/jpeg")},
            params={"subject": subject},
        )
        resp.raise_for_status()
        return resp.json()


async def delete_subject(subject: str) -> None:
    async with _async_client() as client:
        resp = await client.delete(f"/api/v1/recognition/subjects/{subject}")
        if resp.status_code not in (200, 404):
            resp.raise_for_status()


async def health_check() -> bool:
    try:
        async with httpx.AsyncClient(base_url=settings.compreface_url, timeout=5.0) as client:
            # GET subjects list — works with any valid API key, standard CompreFace endpoint
            resp = await client.get(
                "/api/v1/recognition/subjects",
                headers={"x-api-key": settings.compreface_api_key},
            )
            return resp.status_code == 200
    except Exception:
        return False
