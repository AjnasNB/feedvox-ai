"""
Transcription API - Single Upload Endpoint
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging

from services.transcription_service import TranscriptionService
from database.models import Transcription
from database.db_setup import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload", response_model=Dict[str, Any])
async def transcribe_audio_upload(
    audio_file: UploadFile = File(...),
    language: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Upload and transcribe audio file
    
    Args:
        audio_file: Audio file upload (.wav, .mp3, .m4a, .flac, .ogg, .aac, .mp4)
        language: Language code (auto-detect if None)
        
    Returns:
        {
            "success": True,
            "message": "Audio transcribed successfully", 
            "transcription_id": "uuid-string",
            "text": "transcribed text...",
            "duration_seconds": 195.58,
            "processing_time_seconds": 71.35
        }
    """
    try:
        # Validate file type
        if not audio_file.content_type or not audio_file.content_type.startswith(('audio/', 'video/')):
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Please upload an audio or video file."
            )
        
        # Read audio data
        audio_bytes = await audio_file.read()
        
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        # Get transcription service with NPU support
        transcription_service = TranscriptionService()
        
        # Transcribe audio
        logger.info(f"Transcribing audio file: {audio_file.filename}")
        result = await transcription_service.transcribe_audio_bytes(
            audio_bytes,
            filename=audio_file.filename,
            language=language,
            task="transcribe"
        )
        
        # Store transcription in database
        transcription = Transcription(
            audio_filename=audio_file.filename,
            raw_transcript=result["text"],
            duration_seconds=result.get("duration_seconds"),
            confidence_score=result.get("confidence_score"),
            model_used=result.get("model_used", "whisper-base.en")
        )
        
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        
        # Return in exact format requested
        return {
            "success": True,
            "message": "Audio transcribed successfully",
            "transcription_id": transcription.id,
            "text": result["text"],
            "duration_seconds": result.get("duration_seconds"),
            "processing_time_seconds": result.get("processing_time_seconds")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.get("/models", response_model=Dict[str, Any])
async def get_model_info():
    """Get information about available transcription models"""
    try:
        transcription_service = TranscriptionService()
        model_info = transcription_service.get_model_info()
        
        return {
            "success": True,
            "model_info": model_info,
            "supported_languages": transcription_service.get_supported_languages()
        }
        
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/languages", response_model=Dict[str, Any])
async def get_supported_languages():
    """Get list of supported languages"""
    try:
        transcription_service = TranscriptionService()
        languages = transcription_service.get_supported_languages()
        
        return {
            "success": True,
            "languages": languages
        }
        
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{transcription_id}", response_model=Dict[str, Any])
async def get_transcription(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """Get transcription by ID"""
    try:
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()
        
        if not transcription:
            raise HTTPException(status_code=404, detail="Transcription not found")
        
        return {
            "success": True,
            "transcription": {
                "id": transcription.id,
                "audio_filename": transcription.audio_filename,
                "text": transcription.raw_transcript,
                "duration_seconds": transcription.duration_seconds,
                "confidence_score": transcription.confidence_score,
                "model_used": transcription.model_used,
                "created_at": transcription.created_at.isoformat(),
                "updated_at": transcription.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transcription: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=Dict[str, Any])
async def list_transcriptions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List transcriptions with pagination"""
    try:
        transcriptions = db.query(Transcription).offset(skip).limit(limit).all()
        total = db.query(Transcription).count()
        
        return {
            "success": True,
            "transcriptions": [
                {
                    "id": t.id,
                    "audio_filename": t.audio_filename,
                    "text": t.raw_transcript[:200] + "..." if len(t.raw_transcript) > 200 else t.raw_transcript,
                    "duration_seconds": t.duration_seconds,
                    "confidence_score": t.confidence_score,
                    "model_used": t.model_used,
                    "created_at": t.created_at.isoformat()
                }
                for t in transcriptions
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error listing transcriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{transcription_id}", response_model=Dict[str, Any])
async def delete_transcription(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """Delete transcription by ID"""
    try:
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()
        
        if not transcription:
            raise HTTPException(status_code=404, detail="Transcription not found")
        
        db.delete(transcription)
        db.commit()
        
        return {
            "success": True,
            "message": "Transcription deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting transcription: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-sample", response_model=Dict[str, Any])
async def test_with_sample_audio(
    db: Session = Depends(get_db)
):
    """Test transcription with the sample audio file"""
    try:
        # Use the sample audio from the original project
        sample_audio_path = "../simple-whisper-transcription-main/sampleaduio/doctor_patient_transcript.wav"
        
        transcription_service = TranscriptionService()
        
        # Check if sample file exists
        import os
        if not os.path.exists(sample_audio_path):
            raise HTTPException(
                status_code=404, 
                detail="Sample audio file not found. Please ensure the simple-whisper-transcription-main project is in the parent directory."
            )
        
        # Transcribe the sample
        result = await transcription_service.transcribe_audio_file(sample_audio_path)
        
        # Store in database
        transcription = Transcription(
            audio_filename="doctor_patient_transcript.wav",
            raw_transcript=result["text"],
            duration_seconds=result.get("duration_seconds"),
            confidence_score=result.get("confidence_score"),
            model_used=result.get("model_used", "whisper-base.en")
        )
        
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        
        return {
            "success": True,
            "message": "Sample audio transcribed successfully",
            "transcription_id": transcription.id,
            "text": result["text"],
            "duration_seconds": result.get("duration_seconds"),
            "processing_time_seconds": result.get("processing_time_seconds")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing with sample audio: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 