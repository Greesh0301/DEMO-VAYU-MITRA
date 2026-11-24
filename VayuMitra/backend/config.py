import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
DATABASE_DIR = os.path.join(BASE_DIR, "database")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

DATABASE_PATH = os.environ.get("VAYUMITRA_DB_PATH", os.path.join(DATABASE_DIR, "vayumitra.db"))
UPLOAD_FOLDER = os.environ.get("VAYUMITRA_UPLOAD_FOLDER", os.path.join(DATABASE_DIR, "uploads"))



class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "vayumitra-dev-secret-change-in-production")
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))

    # External Environmental & Routing APIs
    # Open-Meteo and OSRM work out of the box with no API key required.
    # Optional keys below enable secondary provider enrichment when configured.
    OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    AQICN_API_TOKEN = os.environ.get("AQICN_API_TOKEN", "").strip()

    DEFAULT_CITY = os.environ.get("VAYUMITRA_DEFAULT_CITY", "Mumbai")
    MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    HTTP_TIMEOUT = 10
