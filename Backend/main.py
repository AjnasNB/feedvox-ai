#!/usr/bin/env python3
"""
FeedVox AI - Medical Transcription and Coding Backend
Main FastAPI application
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
import os

from api.transcription import router as transcription_router
from api.notes import router as notes_router
from api.medical_codes import router as medical_codes_router
from database.db_setup import initialize_database
from services.transcription_service import TranscriptionService
from services.llm_service import LLMService
from services.medical_coding_service import MedicalCodingService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting FeedVox AI Backend...")
    
    # Initialize database
    await initialize_database()
    
    # Initialize services
    app.state.transcription_service = TranscriptionService()
    app.state.llm_service = LLMService()
    app.state.medical_coding_service = MedicalCodingService()
    
    logger.info("✅ FeedVox AI Backend started successfully!")
    
    yield
    
    logger.info("🔄 Shutting down FeedVox AI Backend...")

# Create FastAPI app
app = FastAPI(
    title="FeedVox AI",
    description="Medical Transcription and Coding Backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for UI
if os.path.exists("ui"):
    app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")
    
    @app.get("/ui")
    async def serve_ui():
        """Serve the UI"""
        return FileResponse("ui/index.html")

# Include routers
app.include_router(transcription_router, prefix="/api/v1/transcription", tags=["transcription"])
app.include_router(notes_router, prefix="/api/v1/notes", tags=["notes"])
app.include_router(medical_codes_router, prefix="/api/v1/medical-codes", tags=["medical-codes"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FeedVox AI - Medical Transcription and Coding Backend",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "FeedVox AI"}

@app.get("/status")
async def get_status():
    """Get system status"""
    return {
        "transcription_service": "ready",
        "llm_service": "ready", 
        "medical_coding_service": "ready",
        "database": "connected"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="localhost",
        port=7717,
        reload=True,
        log_level="info"
    ) 