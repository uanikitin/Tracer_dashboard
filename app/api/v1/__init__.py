"""API v1 module."""
from fastapi import APIRouter

from app.api.v1 import auth, sites, wells, sampling, telegram

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(sites.router, prefix="/sites", tags=["sites"])
api_router.include_router(wells.router, prefix="/wells", tags=["wells"])
api_router.include_router(sampling.router, prefix="/sampling", tags=["sampling"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
