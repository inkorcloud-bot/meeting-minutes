"""API module - REST API endpoints"""
from app.api.meetings import router as meetings_router

__all__ = ["meetings_router"]

from app.api.upload import router as upload_router

__all__ = ["upload_router"]
