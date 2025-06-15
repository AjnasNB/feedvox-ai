"""
Database models for FeedVox AI
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Transcription(Base):
    """Transcription model"""
    __tablename__ = "transcriptions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    audio_filename = Column(String, nullable=True)
    raw_transcript = Column(Text, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    model_used = Column(String, default="whisper-base.en")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to notes
    notes = relationship("MedicalNote", back_populates="transcription")

class MedicalNote(Base):
    """Medical note extracted from transcription"""
    __tablename__ = "medical_notes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transcription_id = Column(String, ForeignKey("transcriptions.id"), nullable=True)
    
    # Chief Complaint and History
    chief_complaint = Column(Text, nullable=True)
    history_present_illness = Column(Text, nullable=True)
    past_medical_history = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    social_history = Column(Text, nullable=True)
    family_history = Column(Text, nullable=True)
    
    # Physical Examination
    vital_signs = Column(Text, nullable=True)
    physical_exam = Column(Text, nullable=True)
    
    # Assessment and Plan
    assessment = Column(Text, nullable=True)
    plan = Column(Text, nullable=True)
    
    # Additional structured data
    raw_llm_response = Column(Text, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transcription = relationship("Transcription", back_populates="notes")
    medical_codes = relationship("MedicalCodeAssignment", back_populates="medical_note")

class ICDCode(Base):
    """ICD-10 codes database"""
    __tablename__ = "icd_codes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    chapter = Column(String(200), nullable=True)
    
    # Relationships
    assignments = relationship("MedicalCodeAssignment", back_populates="icd_code")

class CPTCode(Base):
    """CPT procedure codes database"""
    __tablename__ = "cpt_codes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    section = Column(String(200), nullable=True)
    
    # Relationships
    assignments = relationship("MedicalCodeAssignment", back_populates="cpt_code")

class SNOMEDCode(Base):
    """SNOMED-CT codes database"""
    __tablename__ = "snomed_codes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(String(20), unique=True, nullable=False, index=True)
    fsn = Column(Text, nullable=False)  # Fully Specified Name
    pt = Column(Text, nullable=False)   # Preferred Term
    semantic_tag = Column(String(100), nullable=True)
    
    # Relationships
    assignments = relationship("MedicalCodeAssignment", back_populates="snomed_code")

class MedicalCodeAssignment(Base):
    """Assignment of medical codes to notes"""
    __tablename__ = "medical_code_assignments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    medical_note_id = Column(String, ForeignKey("medical_notes.id"), nullable=False)
    
    # Foreign keys to different code types (nullable since only one will be used)
    icd_code_id = Column(Integer, ForeignKey("icd_codes.id"), nullable=True)
    cpt_code_id = Column(Integer, ForeignKey("cpt_codes.id"), nullable=True)
    snomed_code_id = Column(Integer, ForeignKey("snomed_codes.id"), nullable=True)
    
    # Assignment metadata
    confidence_score = Column(Float, nullable=True)
    assigned_by = Column(String(50), default="auto")  # 'auto' or 'manual'
    section = Column(String(100), nullable=True)  # Which part of the note this relates to
    matched_text = Column(Text, nullable=True)  # The text that matched this code
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    medical_note = relationship("MedicalNote", back_populates="medical_codes")
    icd_code = relationship("ICDCode", back_populates="assignments")
    cpt_code = relationship("CPTCode", back_populates="assignments")
    snomed_code = relationship("SNOMEDCode", back_populates="assignments")

class ProcessingJob(Base):
    """Track processing jobs for async operations"""
    __tablename__ = "processing_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String(50), nullable=False)  # 'transcription', 'note_extraction', 'medical_coding'
    status = Column(String(20), default="pending")  # 'pending', 'processing', 'completed', 'failed'
    progress = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    
    # Input/output data
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 