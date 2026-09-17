"""
DevMind AI - Backend Application Entry Point.

What FastAPI is doing here:
- Initializing the ASGI web application instance.
- Configuring Cross-Origin Resource Sharing (CORS) middleware.
- Registering API routes under the `/api` URL prefix.
- Automating request/response validation and OpenAPI documentation generation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.repositories import router as repositories_router

# Initialize FastAPI Application
app = FastAPI(
    title="DevMind AI Backend",
    description="Software Engineering Intelligence Platform Backend API",
    version="0.1.0",
)

"""
Why CORS is needed:
Cross-Origin Resource Sharing (CORS) is a browser security feature that restricts
web pages from making HTTP requests to a different domain or port than the one
serving the page.

Since the DevMind React frontend runs locally on `http://localhost:5173` and the
FastAPI backend runs on `http://127.0.0.1:8000`, the browser will block API calls
unless explicit CORS permissions are granted here.
"""
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Route Handlers under /api prefix
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(repositories_router, prefix="/api", tags=["Repositories"])


@app.get("/")
async def root():
    """Root route providing service navigation guidance."""
    return {
        "message": "DevMind AI Backend Service Active",
        "health_check": "/api/health",
        "docs": "/docs",
    }
