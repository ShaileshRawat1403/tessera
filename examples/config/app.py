"""Sample app that reads configuration from the environment."""

import os


def config() -> dict:
    return {
        "port": int(os.getenv("APP_PORT", "8000")),
        "token": os.environ["API_TOKEN"],
        "database_url": os.environ.get("DATABASE_URL", ""),
        # CACHE_TTL is read here but not documented in .env.example -> drift
        "cache_ttl": int(os.getenv("CACHE_TTL", "60")),
    }
