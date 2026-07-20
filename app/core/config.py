import os
from pathlib import Path


class Settings:
    PROJECT_NAME = "Project Polaris"
    VERSION = "1.6.0"
    LOG_LEVEL = os.getenv("POLARIS_LOG_LEVEL", "INFO").upper()

    BASE_DIR = Path(__file__).resolve().parents[2]
    DATABASE_FILE = BASE_DIR / "polaris.db"
    DATABASE_URL = f"sqlite:///{DATABASE_FILE}"


settings = Settings()
