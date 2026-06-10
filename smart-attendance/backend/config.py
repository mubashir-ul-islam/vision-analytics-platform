import os
from dotenv import load_dotenv

load_dotenv()


def _parse_source(s: str) -> "int | str":
    """Return int if the source is a numeric device index, otherwise return as-is (RTSP/HTTP URL)."""
    try:
        return int(s)
    except (ValueError, TypeError):
        return s


class Settings:
    compreface_url: str = os.getenv("COMPREFACE_URL", "http://localhost:8000")
    compreface_api_key: str = os.getenv("COMPREFACE_API_KEY", "REPLACE_ME_AFTER_COMPREFACE_SETUP")
    # Accepts a device index ("0", "2") or a full URL ("rtsp://...", "http://...")
    # Falls back to legacy ENTRANCE_CAMERA_INDEX / EXIT_CAMERA_INDEX for backwards compatibility
    entrance_camera_source: str = os.getenv("ENTRANCE_CAMERA_SOURCE", os.getenv("ENTRANCE_CAMERA_INDEX", "0"))
    exit_camera_source: str = os.getenv("EXIT_CAMERA_SOURCE", os.getenv("EXIT_CAMERA_INDEX", "2"))
    recognition_threshold: float = float(os.getenv("RECOGNITION_THRESHOLD", "0.85"))
    recognition_interval_seconds: float = float(os.getenv("RECOGNITION_INTERVAL_SECONDS", "2"))
    cooldown_minutes: float = float(os.getenv("COOLDOWN_MINUTES", "0.083"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:////data/attendance.db")
    backend_cors_origins: list[str] = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000").split(",")

    @property
    def compreface_ready(self) -> bool:
        return self.compreface_api_key != "REPLACE_ME_AFTER_COMPREFACE_SETUP" and bool(self.compreface_api_key)

    def update_api_key(self, key: str):
        self.compreface_api_key = key


settings = Settings()
