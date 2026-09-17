"""
Health Check API Route.

Purpose:
The health check endpoint provides a lightweight mechanism for clients,
load balancers, monitoring tools, and frontend applications to verify that
the DevMind AI backend service is running and accessible.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """
    GET /api/health

    Returns system operational status and service identifier.
    Used for liveness probes, monitoring, and frontend connection verification.
    """
    return HealthResponse(
        status="ok",
        service="DevMind AI backend"
    )
