"""Application settings, read from environment variables / the .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = _int("DB_PORT", 3306)
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "farm_market")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

UPLOAD_DIR = BASE_DIR / "uploads"          # farmer uploads (stored on disk, path stored in MySQL)
MAX_IMAGE_BYTES = 5 * 1024 * 1024          # 5 MB

LOCK_AFTER_FAILURES = 5                    # failed logins before the account is locked
LOCK_MINUTES = 5
IDLE_TIMEOUT_MINUTES = 30                  # automatic sign-out after inactivity

EMIRATES = ["Abu Dhabi", "Dubai", "Sharjah", "Ajman", "Umm Al Quwain", "Ras Al Khaimah", "Fujairah"]
CROP_CATEGORIES = ["vegetable", "fruit", "leafy", "herb"]
CYCLE_STATUSES = ["PLANNED", "GROWING", "HARVESTING", "COMPLETED", "CANCELLED"]
REQUEST_STATUSES = ["SUBMITTED", "PARTIALLY_ALLOCATED", "ALLOCATED", "PARTIALLY_FULFILLED",
                    "FULFILLED", "CLOSED", "CANCELLED"]
OPEN_STATUSES = ["SUBMITTED", "PARTIALLY_ALLOCATED", "ALLOCATED", "PARTIALLY_FULFILLED"]
