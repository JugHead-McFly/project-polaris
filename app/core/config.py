from pathlib import Path


class Settings:
    PROJECT_NAME = "Project Polaris"
    VERSION = "1.3.0"

    BASE_DIR = Path(__file__).resolve().parents[2]
    DATABASE_FILE = BASE_DIR / "polaris.db"
    DATABASE_URL = f"sqlite:///{DATABASE_FILE}"


settings = Settings()
