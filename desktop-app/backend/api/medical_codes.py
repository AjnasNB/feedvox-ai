"""
Medical Codes API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any, List
import logging
from sqlalchemy.orm import Session

from services.medical_coding_service import MedicalCodingService
from database.models import ICDCode, CPTCode, SNOMEDCode, MedicalCodeAssignment
from database.db_setup import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/search", response_model=Dict[str, Any])
async def search_medical_codes(
    query: str = Query(..., description="Search query for medical codes"),
    code_type: str = Query("all", description="Type of codes to search: all, icd, cpt, snomed"),
    limit: int = Query(10, description="Maximum number of results to return"),
    db: Session = Depends(get_db)
):
    """
    Search medical codes by query
    
    Args:
        query: Search term
        code_type: Type of codes to search (all, icd, cpt, snomed)
        limit: Maximum results to return
        
    Returns:
        List of matching medical codes
    """
    try:
        if len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Query must be at least 2 characters long")
        
        medical_coding_service = MedicalCodingService()
        results = await medical_coding_service.search_codes(
            query=query,
            code_type=code_type.lower(),
            limit=limit
        )
        
        return {
            "success": True,
            "query": query,
            "code_type": code_type,
            "results": results,
            "total_results": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching medical codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/icd/search", response_model=Dict[str, Any])
async def search_icd_codes(
    query: str = Query(..., description="Search query for ICD codes"),
    limit: int = Query(10, description="Maximum number of results to return"),
    db: Session = Depends(get_db)
):
    """Search ICD-10 codes by query"""
    try:
        if len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Query must be at least 2 characters long")
        
        medical_coding_service = MedicalCodingService()
        results = await medical_coding_service.search_codes(
            query=query,
            code_type="icd",
            limit=limit
        )
        
        return {
            "success": True,
            "query": query,
            "code_type": "icd",
            "results": results,
            "total_results": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching ICD codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cpt/search", response_model=Dict[str, Any])
async def search_cpt_codes(
    query: str = Query(..., description="Search query for CPT codes"),
    limit: int = Query(10, description="Maximum number of results to return"),
    db: Session = Depends(get_db)
):
    """Search CPT codes by query"""
    try:
        if len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Query must be at least 2 characters long")
        
        medical_coding_service = MedicalCodingService()
        results = await medical_coding_service.search_codes(
            query=query,
            code_type="cpt",
            limit=limit
        )
        
        return {
            "success": True,
            "query": query,
            "code_type": "cpt",
            "results": results,
            "total_results": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching CPT codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/snomed/search", response_model=Dict[str, Any])
async def search_snomed_codes(
    query: str = Query(..., description="Search query for SNOMED codes"),
    limit: int = Query(10, description="Maximum number of results to return"),
    db: Session = Depends(get_db)
):
    """Search SNOMED-CT codes by query"""
    try:
        if len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Query must be at least 2 characters long")
        
        medical_coding_service = MedicalCodingService()
        results = await medical_coding_service.search_codes(
            query=query,
            code_type="snomed",
            limit=limit
        )
        
        return {
            "success": True,
            "query": query,
            "code_type": "snomed",
            "results": results,
            "total_results": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching SNOMED codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/icd/{code}", response_model=Dict[str, Any])
async def get_icd_code(
    code: str,
    db: Session = Depends(get_db)
):
    """Get specific ICD-10 code details"""
    try:
        icd_code = db.query(ICDCode).filter(ICDCode.code == code).first()
        
        if not icd_code:
            raise HTTPException(status_code=404, detail="ICD-10 code not found")
        
        return {
            "success": True,
            "code": {
                "id": icd_code.id,
                "code": icd_code.code,
                "description": icd_code.description,
                "category": icd_code.category,
                "chapter": icd_code.chapter
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ICD code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cpt/{code}", response_model=Dict[str, Any])
async def get_cpt_code(
    code: str,
    db: Session = Depends(get_db)
):
    """Get specific CPT code details"""
    try:
        cpt_code = db.query(CPTCode).filter(CPTCode.code == code).first()
        
        if not cpt_code:
            raise HTTPException(status_code=404, detail="CPT code not found")
        
        return {
            "success": True,
            "code": {
                "id": cpt_code.id,
                "code": cpt_code.code,
                "description": cpt_code.description,
                "category": cpt_code.category,
                "section": cpt_code.section
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting CPT code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/snomed/{concept_id}", response_model=Dict[str, Any])
async def get_snomed_code(
    concept_id: str,
    db: Session = Depends(get_db)
):
    """Get specific SNOMED-CT code details"""
    try:
        snomed_code = db.query(SNOMEDCode).filter(SNOMEDCode.concept_id == concept_id).first()
        
        if not snomed_code:
            raise HTTPException(status_code=404, detail="SNOMED-CT code not found")
        
        return {
            "success": True,
            "code": {
                "id": snomed_code.id,
                "concept_id": snomed_code.concept_id,
                "fsn": snomed_code.fsn,
                "pt": snomed_code.pt,
                "semantic_tag": snomed_code.semantic_tag
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SNOMED code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/icd", response_model=Dict[str, Any])
async def list_icd_codes(
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """List ICD-10 codes with pagination and filtering"""
    try:
        query = db.query(ICDCode)
        
        if category:
            query = query.filter(ICDCode.category.ilike(f"%{category}%"))
        
        codes = query.offset(skip).limit(limit).all()
        total = query.count()
        
        return {
            "success": True,
            "codes": [
                {
                    "id": code.id,
                    "code": code.code,
                    "description": code.description,
                    "category": code.category,
                    "chapter": code.chapter
                }
                for code in codes
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
            "filters": {"category": category} if category else {}
        }
        
    except Exception as e:
        logger.error(f"Error listing ICD codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cpt", response_model=Dict[str, Any])
async def list_cpt_codes(
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """List CPT codes with pagination and filtering"""
    try:
        query = db.query(CPTCode)
        
        if category:
            query = query.filter(CPTCode.category.ilike(f"%{category}%"))
        
        codes = query.offset(skip).limit(limit).all()
        total = query.count()
        
        return {
            "success": True,
            "codes": [
                {
                    "id": code.id,
                    "code": code.code,
                    "description": code.description,
                    "category": code.category,
                    "section": code.section
                }
                for code in codes
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
            "filters": {"category": category} if category else {}
        }
        
    except Exception as e:
        logger.error(f"Error listing CPT codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/snomed", response_model=Dict[str, Any])
async def list_snomed_codes(
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    semantic_tag: Optional[str] = Query(None, description="Filter by semantic tag"),
    db: Session = Depends(get_db)
):
    """List SNOMED-CT codes with pagination and filtering"""
    try:
        query = db.query(SNOMEDCode)
        
        if semantic_tag:
            query = query.filter(SNOMEDCode.semantic_tag.ilike(f"%{semantic_tag}%"))
        
        codes = query.offset(skip).limit(limit).all()
        total = query.count()
        
        return {
            "success": True,
            "codes": [
                {
                    "id": code.id,
                    "concept_id": code.concept_id,
                    "fsn": code.fsn,
                    "pt": code.pt,
                    "semantic_tag": code.semantic_tag
                }
                for code in codes
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
            "filters": {"semantic_tag": semantic_tag} if semantic_tag else {}
        }
        
    except Exception as e:
        logger.error(f"Error listing SNOMED codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=Dict[str, Any])
async def get_code_statistics(
    db: Session = Depends(get_db)
):
    """Get statistics about medical codes in the database"""
    try:
        icd_count = db.query(ICDCode).count()
        cpt_count = db.query(CPTCode).count()
        snomed_count = db.query(SNOMEDCode).count()
        assignments_count = db.query(MedicalCodeAssignment).count()
        
        # Get unique categories
        icd_categories = db.query(ICDCode.category).distinct().all()
        cpt_categories = db.query(CPTCode.category).distinct().all()
        snomed_tags = db.query(SNOMEDCode.semantic_tag).distinct().all()
        
        return {
            "success": True,
            "statistics": {
                "total_codes": {
                    "icd": icd_count,
                    "cpt": cpt_count,
                    "snomed": snomed_count,
                    "total": icd_count + cpt_count + snomed_count
                },
                "assignments": assignments_count,
                "categories": {
                    "icd_categories": len([c[0] for c in icd_categories if c[0]]),
                    "cpt_categories": len([c[0] for c in cpt_categories if c[0]]),
                    "snomed_semantic_tags": len([c[0] for c in snomed_tags if c[0]])
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting code statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assignments/{note_id}", response_model=Dict[str, Any])
async def get_note_code_assignments(
    note_id: str,
    db: Session = Depends(get_db)
):
    """Get all medical code assignments for a specific note"""
    try:
        assignments = db.query(MedicalCodeAssignment).filter(
            MedicalCodeAssignment.medical_note_id == note_id
        ).all()
        
        if not assignments:
            return {
                "success": True,
                "note_id": note_id,
                "assignments": {
                    "icd_codes": [],
                    "cpt_codes": [],
                    "snomed_codes": []
                },
                "total_assignments": 0
            }
        
        result = {
            "icd_codes": [],
            "cpt_codes": [],
            "snomed_codes": []
        }
        
        for assignment in assignments:
            assignment_data = {
                "assignment_id": assignment.id,
                "confidence_score": assignment.confidence_score,
                "assigned_by": assignment.assigned_by,
                "section": assignment.section,
                "matched_text": assignment.matched_text,
                "created_at": assignment.created_at.isoformat()
            }
            
            if assignment.icd_code:
                assignment_data.update({
                    "code": assignment.icd_code.code,
                    "description": assignment.icd_code.description,
                    "category": assignment.icd_code.category,
                    "chapter": assignment.icd_code.chapter
                })
                result["icd_codes"].append(assignment_data)
                
            elif assignment.cpt_code:
                assignment_data.update({
                    "code": assignment.cpt_code.code,
                    "description": assignment.cpt_code.description,
                    "category": assignment.cpt_code.category,
                    "section": assignment.cpt_code.section
                })
                result["cpt_codes"].append(assignment_data)
                
            elif assignment.snomed_code:
                assignment_data.update({
                    "concept_id": assignment.snomed_code.concept_id,
                    "fsn": assignment.snomed_code.fsn,
                    "pt": assignment.snomed_code.pt,
                    "semantic_tag": assignment.snomed_code.semantic_tag
                })
                result["snomed_codes"].append(assignment_data)
        
        total_assignments = len(result["icd_codes"]) + len(result["cpt_codes"]) + len(result["snomed_codes"])
        
        return {
            "success": True,
            "note_id": note_id,
            "assignments": result,
            "total_assignments": total_assignments
        }
        
    except Exception as e:
        logger.error(f"Error getting note code assignments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/assignments/{assignment_id}", response_model=Dict[str, Any])
async def delete_code_assignment(
    assignment_id: str,
    db: Session = Depends(get_db)
):
    """Delete a specific medical code assignment"""
    try:
        assignment = db.query(MedicalCodeAssignment).filter(
            MedicalCodeAssignment.id == assignment_id
        ).first()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Code assignment not found")
        
        db.delete(assignment)
        db.commit()
        
        return {
            "success": True,
            "message": "Code assignment deleted successfully",
            "assignment_id": assignment_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting code assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories", response_model=Dict[str, Any])
async def get_code_categories(
    db: Session = Depends(get_db)
):
    """Get all available categories for filtering"""
    try:
        icd_categories = db.query(ICDCode.category).distinct().all()
        cpt_categories = db.query(CPTCode.category).distinct().all()
        snomed_tags = db.query(SNOMEDCode.semantic_tag).distinct().all()
        
        return {
            "success": True,
            "categories": {
                "icd_categories": sorted([c[0] for c in icd_categories if c[0]]),
                "cpt_categories": sorted([c[0] for c in cpt_categories if c[0]]),
                "snomed_semantic_tags": sorted([c[0] for c in snomed_tags if c[0]])
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting code categories: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 