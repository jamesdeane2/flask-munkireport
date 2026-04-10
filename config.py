"""Configuration management for Flask MunkiReport API."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    # Database
    DATABASE_PATH = os.getenv(
        "DATABASE_PATH",
        "/Volumes/Macintosh HD-1/Users/Shared/munkireport-php/app/db/claude.db.sqlite"
    )

    # API Security
    API_KEY = os.getenv("API_KEY")
    if not API_KEY:
        raise ValueError("API_KEY must be set in environment or .env file")

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")

    # Server
    HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    PORT = int(os.getenv("FLASK_PORT", 5000))

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # SQLite optimization
    SQLITE_TIMEOUT = 30.0
    SQLITE_CHECK_SAME_THREAD = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


def get_config():
    """Get configuration based on environment."""
    env = os.getenv("FLASK_DEBUG", "false").lower()
    if env in ("true", "1", "yes"):
        return DevelopmentConfig()
    return ProductionConfig()
