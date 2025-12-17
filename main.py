from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Routers
from resources import user_match

# ------------------------------------------------------------------------------
# App initialization
# ------------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown.
    """
    # Startup
    logging.info("✅ Service starting up (no database connection).")
    
    yield
    
    # Shutdown
    logging.info("🛑 Matches service shutting down.")

app = FastAPI(
    title="Matches Feature",
    version="1.0.0",
    description=(
        "A microservice for handling match pools, pairwise matches, and "
        "user decisions (accept/reject) between participants."
    ),
    lifespan=lifespan,
)

# ------------------------------------------------------------------------------
# CORS Configuration
# ------------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

# Group by resource type
app.include_router(user_match.router, prefix="/users", tags=["user-match"])

# ------------------------------------------------------------------------------
# Healthcheck
# ------------------------------------------------------------------------------


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "matches", "version": "1.0.0"}
