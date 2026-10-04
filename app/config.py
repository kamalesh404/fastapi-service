# FastAPI Service Configuration

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# App settings
APP_NAME = "FastAPI Service"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Database settings
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR}/data/database.db"
)

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# API settings
API_V1_STR = "/api/v1"
```