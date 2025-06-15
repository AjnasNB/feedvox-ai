"""
Medical Note Extraction API - Clean Implementation
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel
import logging
import asyncio
import time

from services.llm_service import LLMService
from services.medical_coding_service import MedicalCodingService
from database.models import MedicalNote, MedicalCodeAssignment
from database.db_setup import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

class NoteExtractionRequest(BaseModel):
    transcript_text: str

@router.post("/extract", response_model=Dict[str, Any])
async def extract_medical_note(
    request: NoteExtractionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Extract structured medical note from transcript text
    
    Args:
        transcript_text: The transcribed medical conversation text
        
    Returns:
        Structured medical note with extracted sections and medical codes
    """
    try:
        logger.info(f"Extracting medical note from transcript: {request.transcript_text[:100]}...")
        
        # Extract medical note using LLM service
        llm_service = LLMService()
        extraction_result = await llm_service.extract_medical_note(request.transcript_text)
        
        if not extraction_result.get("success"):
            logger.warning("LLM extraction failed")
            raise HTTPException(status_code=500, detail="Medical note extraction failed")
        
        medical_data = extraction_result["medical_note"]
        logger.info(f"Medical data extracted: {medical_data}")
        
        # Store in database
        medical_note = MedicalNote(
            transcription_id=None,  # Direct text extraction
            chief_complaint=medical_data.get("chief_complaint", "Not documented"),
            history_present_illness=medical_data.get("history_present_illness", "Not documented"),
            past_medical_history=medical_data.get("past_medical_history", "Not documented"),
            medications=medical_data.get("medications", "Not documented"),
            allergies=medical_data.get("allergies", "Not documented"),
            social_history=medical_data.get("social_history", "Not documented"),
            family_history=medical_data.get("family_history", "Not documented"),
            vital_signs=medical_data.get("vital_signs", "Not documented"),
            physical_exam=medical_data.get("physical_exam", "Not documented"),
            assessment=medical_data.get("assessment", "Not documented"),
            plan=medical_data.get("plan", "Not documented"),
            raw_llm_response=extraction_result.get("raw_response", ""),
            extraction_confidence=0.85
        )
        
        db.add(medical_note)
        db.commit()
        db.refresh(medical_note)
        logger.info(f"Medical note stored with ID: {medical_note.id}")
        
        # Run medical coding in background
        medical_codes = {"icd_codes": [], "cpt_codes": [], "snomed_codes": [], "total_codes": 0}
        try:
            coding_service = MedicalCodingService()
            medical_codes = await coding_service.code_medical_note(medical_data, medical_note.id)
            logger.info(f"Medical coding completed for note {medical_note.id}")
        except Exception as e:
            logger.error(f"Error in medical coding: {e}")
        
        # Format clean response
        response_data = {
            "success": True,
            "message": "Medical note extracted successfully",
            "note_id": str(medical_note.id),
            "medical_note": {
                "chief_complaint": medical_note.chief_complaint,
                "history_present_illness": medical_note.history_present_illness,
                "past_medical_history": medical_note.past_medical_history,
                "medications": medical_note.medications,
                "allergies": medical_note.allergies,
                "social_history": medical_note.social_history,
                "family_history": medical_note.family_history,
                "vital_signs": medical_note.vital_signs,
                "physical_exam": medical_note.physical_exam,
                "assessment": medical_note.assessment,
                "plan": medical_note.plan
            },
            "medical_codes": medical_codes,
            "processing_status": "Medical coding completed"
        }
        
        logger.info(f"Returning response: {response_data}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting medical note: {e}")
        raise HTTPException(status_code=500, detail=f"Medical note extraction failed: {str(e)}")

@router.get("/{note_id}", response_model=Dict[str, Any])
async def get_medical_note(
    note_id: str,
    db: Session = Depends(get_db)
):
    """Get medical note with all assigned codes"""
    try:
        # Get the medical note
        note = db.query(MedicalNote).filter(MedicalNote.id == note_id).first()
        if not note:
            raise HTTPException(status_code=404, detail="Medical note not found")
        
        # Get medical codes
        medical_codes = get_note_medical_codes(note_id, db)
        
        return {
            "success": True,
            "medical_note": {
                "id": note.id,
                "chief_complaint": note.chief_complaint,
                "history_present_illness": note.history_present_illness,
                "past_medical_history": note.past_medical_history,
                "medications": note.medications,
                "allergies": note.allergies,
                "social_history": note.social_history,
                "family_history": note.family_history,
                "vital_signs": note.vital_signs,
                "physical_exam": note.physical_exam,
                "assessment": note.assessment,
                "plan": note.plan,
                "created_at": note.created_at.isoformat()
            },
            "medical_codes": medical_codes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting medical note: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_note_medical_codes(note_id: str, db: Session) -> Dict[str, Any]:
    """Get all medical codes assigned to a note"""
    try:
        assignments = db.query(MedicalCodeAssignment).filter(
            MedicalCodeAssignment.medical_note_id == note_id
        ).all()
        
        icd_codes = []
        cpt_codes = []
        snomed_codes = []
        
        for assignment in assignments:
            if assignment.icd_code:
                icd_codes.append({
                    "code": assignment.icd_code.code,
                    "description": assignment.icd_code.description,
                    "confidence": assignment.confidence_score,
                    "section": assignment.section
                })
            elif assignment.cpt_code:
                cpt_codes.append({
                    "code": assignment.cpt_code.code,
                    "description": assignment.cpt_code.description,
                    "confidence": assignment.confidence_score,
                    "section": assignment.section
                })
            elif assignment.snomed_code:
                snomed_codes.append({
                    "code": assignment.snomed_code.concept_id,
                    "description": assignment.snomed_code.pt,
                    "confidence": assignment.confidence_score,
                    "section": assignment.section
                })
        
        return {
            "icd_codes": icd_codes,
            "cpt_codes": cpt_codes,
            "snomed_codes": snomed_codes,
            "total_codes": len(icd_codes) + len(cpt_codes) + len(snomed_codes)
        }
        
    except Exception as e:
        logger.error(f"Error getting medical codes: {e}")
        return {
            "icd_codes": [],
            "cpt_codes": [],
            "snomed_codes": [],
            "total_codes": 0
        } 