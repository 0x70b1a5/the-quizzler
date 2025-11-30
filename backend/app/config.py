"""
Configuration loaded from environment variables.
"""

import os
from functools import lru_cache


@lru_cache
def get_config():
    """Get configuration from environment variables."""
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    return {
        "backend_host": host,
        "backend_port": port,
        "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "additional_cors_origins": os.getenv("ADDITIONAL_CORS_ORIGINS", ""),
        # Public URL for generating client-facing URLs (uploads, etc.)
        # Falls back to local URL if not set
        "public_url": os.getenv("PUBLIC_URL", f"http://{host}:{port}"),
    }


def get_backend_url() -> str:
    """Get the full backend URL (internal)."""
    config = get_config()
    return f"http://{config['backend_host']}:{config['backend_port']}"


def get_public_url() -> str:
    """Get the public-facing URL for client requests."""
    return get_config()["public_url"]


def get_frontend_url() -> str:
    """Get the frontend URL."""
    return get_config()["frontend_url"]


def get_cors_origins() -> list[str]:
    """Get allowed CORS origins."""
    config = get_config()
    frontend = config["frontend_url"]
    
    # Start with the primary frontend URL
    origins = [frontend]
    
    # Add localhost variations
    if "localhost" in frontend:
        origins.append(frontend.replace("localhost", "127.0.0.1"))
    elif "127.0.0.1" in frontend:
        origins.append(frontend.replace("127.0.0.1", "localhost"))
    
    # Add any additional origins from environment
    additional = config["additional_cors_origins"]
    if additional:
        origins.extend([o.strip() for o in additional.split(",") if o.strip()])
    
    return origins

