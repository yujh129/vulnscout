from fastapi import APIRouter

from vulnscout.api.scans import router as scans_router
from vulnscout.api.patches import router as patches_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(scans_router, prefix="/scans", tags=["scans"])
api_router.include_router(patches_router, prefix="/patches", tags=["patches"])
