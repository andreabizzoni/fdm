from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, Base
from app.routers import upload, forecast
import app.models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Steel Production API",
    description="API for steel plant production plans and forecasting",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(upload.router)
app.include_router(forecast.router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
