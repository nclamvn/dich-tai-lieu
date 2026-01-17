"""
CORS Configuration for PrismyDoc Integration
"""

from fastapi.middleware.cors import CORSMiddleware
import os

def setup_cors(app):
    """Configure CORS for PrismyDoc frontend"""

    origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Job-ID", "X-Progress", "Content-Disposition"],
    )

    return app
