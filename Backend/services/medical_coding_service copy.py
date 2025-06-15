"""
Medical Coding Service
Matches extracted medical notes with ICD-10, CPT, and SNOMED codes
"""

import logging
import os
import yaml
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, func
from fuzzywuzzy import fuzz, process
import re

from database.models import ICDCode, CPTCode, SNOMEDCode, MedicalCodeAssignment
from database.db_setup import SessionLocal

logger = logging.getLogger(__name__)

class MedicalCodingService:
    """Service for automatic medical coding using fuzzy matching"""
    
    def __init__(self, config_path: str = "../config.yaml"):
        """
        Initialize medical coding service
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.confidence_threshold = self._get_confidence_threshold()
        self.max_codes_per_type = self._get_max_codes_per_type()
        self.enable_fuzzy_matching = self._get_fuzzy_matching_enabled()
        
        # Optimized caches - only load essential codes
        self.icd_cache = {}
        self.cpt_cache = {}
        self.snomed_cache = {}
        self._load_essential_codes_cache()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {config_path}")
                return config
            else:
                logger.warning(f"Config file {config_path} not found, using defaults")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "medical_coding": {
                "confidence_threshold": 0.75,
                "max_codes_per_type": 5,
                "enable_fuzzy_matching": True,
                "load_common_codes_only": True,
                "max_cache_size": 10000
            }
        }
    
    def _get_confidence_threshold(self) -> float:
        """Get confidence threshold from config or environment"""
        threshold = self.config.get("medical_coding", {}).get("confidence_threshold")
        if threshold:
            return float(threshold)
        
        threshold = os.getenv("MEDICAL_CODING_CONFIDENCE_THRESHOLD")
        if threshold:
            return float(threshold)
        
        return 0.75  # Default higher threshold for accuracy
    
    def _get_max_codes_per_type(self) -> int:
        """Get max codes per type from config"""
        max_codes = self.config.get("medical_coding", {}).get("max_codes_per_type", 5)
        return int(max_codes)
    
    def _get_fuzzy_matching_enabled(self) -> bool:
        """Get fuzzy matching setting from config"""
        return self.config.get("medical_coding", {}).get("enable_fuzzy_matching", True)
    
    def _load_essential_codes_cache(self):
        """Load only essential/common medical codes into memory for faster matching"""
        try:
            with SessionLocal() as db:
                max_cache_size = self.config.get("medical_coding", {}).get("max_cache_size", 10000)
                
                # Load common ICD codes - focus on primary care conditions
                common_icd_patterns = [
                    'hypertension', 'diabetes', 'chest pain', 'depression', 'anxiety',
                    'back pain', 'headache', 'upper respiratory', 'pneumonia', 'bronchitis',
                    'gastroesophageal reflux', 'arthritis', 'asthma', 'copd', 'heart failure',
                    'atrial fibrillation', 'migraine', 'obesity', 'hyperlipidemia'
                ]
                
                icd_codes = db.query(ICDCode).filter(
                    or_(*[ICDCode.description.ilike(f'%{pattern}%') for pattern in common_icd_patterns])
                ).limit(max_cache_size // 3).all()
                
                # If not enough common codes found, get most frequently used ones
                if len(icd_codes) < 1000:
                    additional_codes = db.query(ICDCode).filter(
                        ~ICDCode.id.in_([code.id for code in icd_codes])
                    ).order_by(ICDCode.code).limit(2000).all()
                    icd_codes.extend(additional_codes)
                
                self.icd_cache = {
                    code.id: {
                        "code": code.code,
                        "description": code.description.lower(),
                        "category": code.category,
                        "chapter": code.chapter
                    }
                    for code in icd_codes
                }
                
                # Load common CPT codes - focus on office visits and common procedures
                common_cpt_patterns = [
                    'office visit', 'evaluation and management', 'consultation',
                    'examination', 'preventive', 'immunization', 'injection',
                    'blood pressure', 'diabetes', 'follow-up', 'counseling'
                ]
                
                cpt_codes = db.query(CPTCode).filter(
                    or_(*[CPTCode.description.ilike(f'%{pattern}%') for pattern in common_cpt_patterns])
                ).limit(max_cache_size // 3).all()
                
                # Add essential E&M codes
                essential_cpt_codes = ['99213', '99214', '99215', '99212', '99211', '99395', '99396']
                essential_cpts = db.query(CPTCode).filter(
                    CPTCode.code.in_(essential_cpt_codes)
                ).all()
                cpt_codes.extend(essential_cpts)
                
                self.cpt_cache = {
                    code.id: {
                        "code": code.code,
                        "description": code.description.lower(),
                        "category": code.category,
                        "section": code.section
                    }
                    for code in cpt_codes
                }
                
                # Load essential SNOMED codes - focus on common clinical concepts
                common_snomed_patterns = [
                    'hypertension', 'diabetes', 'pain', 'examination', 'blood pressure',
                    'medication', 'treatment', 'diagnosis', 'assessment', 'disorder'
                ]
                
                snomed_codes = db.query(SNOMEDCode).filter(
                    or_(*[SNOMEDCode.pt.ilike(f'%{pattern}%') for pattern in common_snomed_patterns])
                ).limit(max_cache_size // 3).all()
                
                self.snomed_cache = {
                    code.id: {
                        "concept_id": code.concept_id,
                        "fsn": code.fsn.lower(),
                        "pt": code.pt.lower(),
                        "semantic_tag": code.semantic_tag
                    }
                    for code in snomed_codes
                }
                
                logger.info(f"Loaded {len(self.icd_cache)} ICD, {len(self.cpt_cache)} CPT, {len(self.snomed_cache)} SNOMED codes")
                
        except Exception as e:
            logger.error(f"Error loading essential codes cache: {e}")
    
    def update_config(self, **kwargs) -> None:
        """Update configuration dynamically"""
        medical_coding_config = self.config.setdefault("medical_coding", {})
        
        for key, value in kwargs.items():
            if key == "confidence_threshold":
                self.confidence_threshold = float(value)
                medical_coding_config["confidence_threshold"] = float(value)
            elif key == "max_codes_per_type":
                self.max_codes_per_type = int(value)
                medical_coding_config["max_codes_per_type"] = int(value)
            elif key == "enable_fuzzy_matching":
                self.enable_fuzzy_matching = bool(value)
                medical_coding_config["enable_fuzzy_matching"] = bool(value)
        
        logger.info(f"Updated medical coding configuration: {list(kwargs.keys())}")
    
    def _filter_medical_condition_terms(self, terms: List[str]) -> List[str]:
        """Filter terms to only include medical conditions worth coding"""
        # Generic terms that shouldn't be coded
        generic_terms = {
            'pain', 'exam', 'test', 'visit', 'follow', 'up', 'check', 'assessment',
            'evaluation', 'management', 'consultation', 'office', 'appointment',
            'procedure', 'treatment', 'therapy', 'medication', 'drug', 'symptoms',
            'history', 'patient', 'doctor', 'physician', 'nurse', 'medical', 'clinical'
        }
        
        filtered_terms = []
        for term in terms:
            if len(term) < 4:  # Require minimum length
                continue
            
            term_lower = term.lower().strip()
            
            # Skip generic terms
            if term_lower in generic_terms:
                continue
            
            # Only include terms that look like actual medical conditions
            if self._is_medical_condition(term_lower):
                filtered_terms.append(term)
        
        return filtered_terms
    
    def _get_dynamic_threshold(self, term: str, code_type: str) -> float:
        """Get dynamic threshold based on term specificity and code type"""
        base_threshold = self.confidence_threshold * 100
        
        # Adjust based on term length and specificity
        if len(term) >= 15:  # Very specific terms
            return base_threshold - 10
        elif len(term) >= 10:  # Moderately specific
            return base_threshold - 5
        else:  # Short terms need higher confidence
            return base_threshold + 5
    
    def _filter_final_matches(self, matches: List[Dict[str, Any]], code_type: str) -> List[Dict[str, Any]]:
        """Apply final filtering to remove duplicates and low-confidence matches"""
        # Remove duplicates based on code
        seen_codes = set()
        filtered_matches = []
        
        # Sort by confidence first
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        
        for match in matches:
            code_key = match.get("code") or match.get("concept_id", "")
            min_confidence = self.confidence_threshold
            
            if code_key not in seen_codes and match["confidence"] >= min_confidence:
                seen_codes.add(code_key)
                filtered_matches.append(match)
                
                # Limit based on configuration
                if len(filtered_matches) >= self.max_codes_per_type:
                    break
        
        return filtered_matches
    
    async def code_medical_note(
        self, 
        medical_note: Dict[str, str],
        note_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate medical codes for a medical note
        
        Args:
            medical_note: Structured medical note
            note_id: Medical note ID
            
        Returns:
            Dict with lists of matched codes by type
        """
        try:
            results = {
                "icd_codes": [],
                "cpt_codes": [],
                "snomed_codes": []
            }
            
            # Extract key terms from different sections
            diagnostic_terms = self._extract_diagnostic_terms(medical_note)
            procedure_terms = self._extract_procedure_terms(medical_note)
            
            logger.info(f"Extracted diagnostic terms: {diagnostic_terms}")
            logger.info(f"Extracted procedure terms: {procedure_terms}")
            
            # Match ICD codes for diagnoses
            if diagnostic_terms:
                icd_matches = await self._match_icd_codes(diagnostic_terms)
                results["icd_codes"] = icd_matches
                logger.info(f"Found {len(icd_matches)} ICD matches")
            
            # Match CPT codes for procedures
            if procedure_terms:
                cpt_matches = await self._match_cpt_codes(procedure_terms)
                results["cpt_codes"] = cpt_matches
                logger.info(f"Found {len(cpt_matches)} CPT matches")
            
            # Match SNOMED codes for clinical concepts
            all_terms = diagnostic_terms + procedure_terms
            if all_terms:
                snomed_matches = await self._match_snomed_codes(all_terms)
                results["snomed_codes"] = snomed_matches
                logger.info(f"Found {len(snomed_matches)} SNOMED matches")
            
            # Store assignments in database
            await self._store_code_assignments(note_id, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error coding medical note: {e}")
            return {"icd_codes": [], "cpt_codes": [], "snomed_codes": []}
    
    def _extract_diagnostic_terms(self, medical_note: Dict[str, str]) -> List[str]:
        """Extract diagnostic terms from medical note"""
        diagnostic_sections = [
            "chief_complaint",
            "history_present_illness", 
            "assessment",
            "past_medical_history"
        ]
        
        terms = []
        for section in diagnostic_sections:
            content = medical_note.get(section, "")
            if content and content.lower() != "not mentioned":
                # Extract key medical terms
                extracted = self._extract_medical_terms(content)
                terms.extend(extracted)
        
        return list(set(terms))  # Remove duplicates
    
    def _extract_procedure_terms(self, medical_note: Dict[str, str]) -> List[str]:
        """Extract procedure terms from medical note"""
        procedure_sections = [
            "plan",
            "physical_exam",
            "assessment",  # Assessment often contains procedure plans
            "history_present_illness"  # May mention tests/procedures done
        ]
        
        terms = []
        for section in procedure_sections:
            content = medical_note.get(section, "")
            if content and content.lower() != "not documented":
                # Look for procedure-related terms
                extracted = self._extract_procedure_keywords(content)
                terms.extend(extracted)
                
                # Also extract any procedure-related phrases from free text
                extracted_phrases = self._extract_procedure_phrases(content)
                terms.extend(extracted_phrases)
                
                # Extract common medical procedures from text
                procedure_patterns = [
                    r"(?:order|ordered|will order|plan to order)\s+([^.]{5,50})",
                    r"(?:ekg|ecg|x-ray|chest x-ray|blood work|lab work|cardiac enzymes|troponin)",
                    r"(?:follow up|follow-up|return|visit|appointment|consultation)",
                    r"(?:evaluation|assessment|examination|exam|check)",
                    r"(?:monitoring|management|counseling|guidance)"
                ]
                
                for pattern in procedure_patterns:
                    matches = re.findall(pattern, content.lower())
                    for match in matches:
                        if isinstance(match, str) and len(match.strip()) > 3:
                            terms.append(match.strip())
        
        # Always include common visit types if plan section exists
        plan_content = medical_note.get("plan", "")
        if plan_content and plan_content.lower() != "not documented":
            terms.extend(["office visit", "evaluation and management", "follow-up visit"])
        
        return list(set(terms))  # Remove duplicates
    
    def _extract_medical_terms(self, text: str) -> List[str]:
        """Extract medical terms from text using patterns"""
        if not text or text.lower() == "not mentioned":
            return []
        
        # Common medical term patterns
        medical_patterns = [
            r'\b\w+itis\b',  # inflammations (bronchitis, arthritis)
            r'\b\w+osis\b',  # conditions (stenosis, fibrosis)
            r'\b\w+opathy\b',  # diseases (neuropathy, cardiomyopathy)
            r'\b\w+algia\b',  # pain (neuralgia, fibromyalgia)
            r'\b\w+emia\b',  # blood conditions (anemia, leukemia)
            r'\b\w+trophy\b',  # growth disorders (hypertrophy, atrophy)
        ]
        
        terms = []
        text_lower = text.lower()
        
        # Extract pattern-based terms
        for pattern in medical_patterns:
            matches = re.findall(pattern, text_lower)
            terms.extend(matches)
        
        # Extract common medical conditions
        common_conditions = [
            "hypertension", "diabetes", "depression", "anxiety", "asthma",
            "copd", "pneumonia", "bronchitis", "heart failure", "stroke",
            "myocardial infarction", "angina", "arrhythmia", "chest pain",
            "shortness of breath", "fever", "headache", "nausea", "vomiting"
        ]
        
        for condition in common_conditions:
            if condition in text_lower:
                terms.append(condition)
        
        # Split sentences and extract noun phrases (simplified)
        sentences = text.split('.')
        for sentence in sentences:
            words = sentence.lower().strip().split()
            if len(words) >= 2 and len(words) <= 5:
                # Look for potential medical terms (2-5 words)
                if any(word in sentence.lower() for word in ['pain', 'syndrome', 'disease', 'disorder', 'condition']):
                    terms.append(sentence.strip())
        
        return [term.strip() for term in terms if len(term.strip()) > 2]
    
    def _extract_procedure_keywords(self, text: str) -> List[str]:
        """Extract procedure-related keywords"""
        if not text or text.lower() == "not documented":
            return []
        
        procedure_keywords = [
            "examination", "exam", "assessment", "test", "screening",
            "biopsy", "surgery", "procedure", "injection", "vaccination",
            "x-ray", "ct scan", "mri", "ultrasound", "ecg", "ekg",
            "blood test", "lab work", "culture", "urinalysis",
            "office visit", "consultation", "follow-up", "follow up",
            "evaluation", "management", "counseling", "guidance",
            "monitoring", "check-up", "visit", "appointment",
            "cardiac enzymes", "troponin", "chest x-ray", "blood work",
            "electrocardiogram", "physical exam", "physical examination",
            "vital signs", "blood pressure check", "diabetes management",
            "medication management", "preventive care", "wellness visit",
            "routine check", "annual physical", "immunization"
        ]
        
        terms = []
        text_lower = text.lower()
        
        for keyword in procedure_keywords:
            if keyword in text_lower:
                terms.append(keyword)
        
        # Also look for "order" or "will order" patterns
        order_patterns = [
            r"(?:order|ordered|will order|plan to order)\s+([a-zA-Z\s]{3,30})",
            r"(?:recommend|prescribe|start|begin)\s+([a-zA-Z\s]{3,30})"
        ]
        
        for pattern in order_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if len(match.strip()) > 3:
                    terms.append(match.strip())
        
        return terms
    
    def _extract_procedure_phrases(self, text: str) -> List[str]:
        """Extract procedure-related phrases from free text"""
        if not text or text.lower() == "not mentioned":
            return []
        
        procedure_phrases = [
            "office visit", "follow-up visit", "consultation",
            "evaluation and management", "e&m", "em visit",
            "annual physical", "routine check", "wellness visit",
            "medication management", "blood pressure check",
            "diabetes management", "cholesterol management"
        ]
        
        terms = []
        text_lower = text.lower()
        
        for phrase in procedure_phrases:
            if phrase in text_lower:
                terms.append(phrase)
        
        return terms
    
    async def _match_icd_codes(self, terms: List[str]) -> List[Dict[str, Any]]:
        """Match terms to ICD-10 codes using optimized fuzzy matching"""
        if not self.enable_fuzzy_matching:
            return []
        
        matches = []
        
        # Filter to only medical condition terms
        filtered_terms = self._filter_medical_condition_terms(terms)
        logger.info(f"Filtered ICD terms: {filtered_terms}")
        
        for term in filtered_terms:
            term_lower = term.lower()
            best_matches = []
            
            # Search through optimized ICD cache
            for icd_id, icd_data in self.icd_cache.items():
                description = icd_data["description"]
                
                # Calculate similarity scores
                if self.enable_fuzzy_matching:
                    token_score = fuzz.token_sort_ratio(term_lower, description)
                    partial_score = fuzz.partial_ratio(term_lower, description)
                    
                    # Use best score
                    best_score = max(token_score, partial_score)
                    
                    # Apply dynamic threshold based on term specificity
                    threshold = self._get_dynamic_threshold(term, "icd")
                    
                    if best_score >= threshold:
                        best_matches.append({
                            "id": icd_id,
                            "code": icd_data["code"],
                            "description": icd_data["description"].title(),
                            "confidence": best_score / 100,
                            "matched_text": term,
                            "section": "diagnosis",
                            "category": icd_data.get("category", "")
                        })
            
            # Sort by confidence and take best matches
            best_matches.sort(key=lambda x: x["confidence"], reverse=True)
            matches.extend(best_matches[:2])  # Top 2 per term
        
        # Remove duplicates and apply final filtering
        return self._filter_final_matches(matches, "icd")
    
    def _is_medical_condition(self, term: str) -> bool:
        """Check if a term represents a medical condition worth coding"""
        # Common medical condition patterns
        medical_patterns = [
            r'\w+itis$',      # inflammations (arthritis, bronchitis)
            r'\w+osis$',      # conditions (stenosis, fibrosis)
            r'\w+opathy$',    # diseases (neuropathy, cardiomyopathy)
            r'\w+algia$',     # pain conditions (neuralgia, fibromyalgia)
            r'\w+emia$',      # blood conditions (anemia, leukemia)
            r'\w+trophy$',    # growth disorders (hypertrophy, atrophy)
        ]
        
        # Check pattern matches
        for pattern in medical_patterns:
            if re.search(pattern, term):
                return True
        
        # Specific medical conditions
        medical_conditions = {
            'hypertension', 'diabetes', 'depression', 'anxiety', 'asthma',
            'copd', 'pneumonia', 'bronchitis', 'heart failure', 'stroke',
            'myocardial infarction', 'angina', 'arrhythmia', 'chest pain',
            'shortness of breath', 'fever', 'headache', 'nausea', 'vomiting',
            'diabetes mellitus', 'type 2 diabetes', 'type 1 diabetes',
            'high blood pressure', 'coronary artery disease', 'atrial fibrillation',
            'congestive heart failure', 'chronic kidney disease', 'osteoarthritis',
            'rheumatoid arthritis', 'gastroesophageal reflux', 'gerd',
            'chronic obstructive pulmonary disease', 'sleep apnea', 'obesity',
            'hyperlipidemia', 'hypercholesterolemia', 'hypothyroidism',
            'hyperthyroidism', 'migraine', 'seizure disorder', 'epilepsy'
        }
        
        return term in medical_conditions
    
    def _has_exact_word_match(self, term: str, description: str) -> bool:
        """Check if term has exact word matches in description"""
        import re
        
        # Split term into words
        term_words = term.split()
        
        # For single word terms, require exact word boundary match
        if len(term_words) == 1:
            pattern = r'\b' + re.escape(term) + r'\b'
            return bool(re.search(pattern, description, re.IGNORECASE))
        
        # For multi-word terms, require all words to be present
        for word in term_words:
            if len(word) > 2:  # Skip very short words
                pattern = r'\b' + re.escape(word) + r'\b'
                if not re.search(pattern, description, re.IGNORECASE):
                    return False
        
        return True
    
    def _is_relevant_icd_match(self, term: str, description: str, code: str) -> bool:
        """Check if an ICD match is relevant and not a false positive"""
        term_lower = term.lower()
        desc_lower = description.lower()
        
        # Skip matches that are too generic or unrelated
        irrelevant_patterns = [
            'follow up', 'follow-up', 'examination', 'visit', 'check',
            'screening', 'monitoring', 'assessment', 'evaluation'
        ]
        
        if any(pattern in term_lower for pattern in irrelevant_patterns):
            return False
        
        # Skip if the match is on a very common word that appears in many descriptions
        common_words = ['with', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for']
        if term_lower in common_words:
            return False
        
        # Ensure the term is actually a significant part of the description
        if len(term) >= 6 and term_lower in desc_lower:
            return True
        
        # For shorter terms, require exact word match
        if len(term) < 6:
            import re
            pattern = r'\b' + re.escape(term_lower) + r'\b'
            return bool(re.search(pattern, desc_lower))
        
        return True
    
    async def _match_cpt_codes(self, terms: List[str]) -> List[Dict[str, Any]]:
        """Match terms to CPT codes using precise fuzzy matching"""
        matches = []
        
        # Define specific procedure terms that should be coded
        valid_procedure_terms = {
            'office visit', 'consultation', 'evaluation and management',
            'follow-up visit', 'annual physical', 'wellness visit',
            'routine check', 'physical examination', 'blood pressure check',
            'diabetes management', 'medication management', 'counseling',
            'preventive care', 'screening', 'immunization', 'vaccination'
        }
        
        # Filter terms to only specific procedure-related ones
        procedure_terms = []
        for term in terms:
            if len(term) < 5:  # Require longer terms
                continue
            term_lower = term.lower().strip()
            
            # Only include specific procedure terms
            if any(valid_term in term_lower for valid_term in valid_procedure_terms):
                procedure_terms.append(term)
            # Or if it contains specific procedure keywords with context
            elif self._is_specific_procedure(term_lower):
                procedure_terms.append(term)
        
        logger.info(f"Filtered CPT terms: {procedure_terms}")
        
        # If no specific procedures found, try to infer common ones
        if not procedure_terms:
            # Look for common visit patterns in the original terms
            for term in terms:
                if any(pattern in term.lower() for pattern in [
                    'office visit', 'follow up', 'consultation', 'evaluation'
                ]):
                    procedure_terms.append('office visit')
                    break
        
        for term in procedure_terms:
            best_matches = []
            term_lower = term.lower()
            
            # Search through CPT cache with stricter matching
            for cpt_id, cpt_data in self.cpt_cache.items():
                description = cpt_data["description"].lower()
                
                # Use fuzzy matching without requiring exact word matches
                token_score = fuzz.token_sort_ratio(term_lower, description)
                partial_score = fuzz.partial_ratio(term_lower, description)
                ratio_score = fuzz.ratio(term_lower, description)
                
                best_score = max(token_score, partial_score, ratio_score)
                
                # Lower threshold for CPT codes
                if best_score >= 70:
                    best_matches.append({
                        "id": cpt_id,
                        "code": cpt_data["code"],
                        "description": cpt_data["description"].title(),
                        "confidence": best_score / 100,
                        "matched_text": term,
                        "section": "procedure"
                    })
            
            # Sort by confidence and take only the best match
            best_matches.sort(key=lambda x: x["confidence"], reverse=True)
            if best_matches:
                matches.append(best_matches[0])
        
        # Remove duplicates and return top matches
        seen_codes = set()
        filtered_matches = []
        for match in matches:
            if match["code"] not in seen_codes and match["confidence"] >= 0.70:
                seen_codes.add(match["code"])
                filtered_matches.append(match)
        
        return filtered_matches[:5]  # Allow more matches
    
    def _is_specific_procedure(self, term: str) -> bool:
        """Check if term represents a specific medical procedure"""
        specific_procedures = {
            'blood test', 'lab work', 'x-ray', 'ct scan', 'mri', 'ultrasound',
            'ecg', 'ekg', 'electrocardiogram', 'biopsy', 'injection',
            'vaccination', 'immunization', 'surgery', 'procedure',
            'endoscopy', 'colonoscopy', 'mammogram', 'pap smear'
        }
        
        return any(proc in term for proc in specific_procedures)
    
    def _is_relevant_cpt_match(self, term: str, description: str) -> bool:
        """Check if a CPT match is relevant"""
        term_lower = term.lower()
        desc_lower = description.lower()
        
        # Ensure it's actually a procedure-related match
        procedure_keywords = [
            'visit', 'exam', 'evaluation', 'management', 'consultation',
            'office', 'follow', 'assessment', 'procedure', 'service'
        ]
        
        # Term should contain procedure keywords
        if not any(keyword in term_lower for keyword in procedure_keywords):
            return False
        
        # Description should also be procedure-related
        if not any(keyword in desc_lower for keyword in procedure_keywords + ['code', 'service']):
            return False
        
        return True
    
    async def _match_snomed_codes(self, terms: List[str]) -> List[Dict[str, Any]]:
        """Match terms to SNOMED-CT codes using precise fuzzy matching"""
        matches = []
        
        for term in terms:
            if len(term) < 4:  # Require longer terms for SNOMED
                continue
                
            best_matches = []
            
            # Search through SNOMED cache (limit search for performance)
            for snomed_id, snomed_data in list(self.snomed_cache.items())[:5000]:
                # Match against both FSN and PT
                fsn_score = fuzz.token_sort_ratio(term.lower(), snomed_data["fsn"])
                pt_score = fuzz.token_sort_ratio(term.lower(), snomed_data["pt"])
                
                max_score = max(fsn_score, pt_score)
                
                # Lower threshold for SNOMED
                if max_score >= 75 and self._is_relevant_snomed_match(term, snomed_data):
                    best_matches.append({
                        "id": snomed_id,
                        "concept_id": snomed_data["concept_id"],
                        "fsn": snomed_data["fsn"].title(),
                        "pt": snomed_data["pt"].title(),
                        "confidence": max_score / 100,
                        "matched_text": term,
                        "section": "clinical_concept"
                    })
            
            # Sort by confidence and take top matches
            best_matches.sort(key=lambda x: x["confidence"], reverse=True)
            matches.extend(best_matches[:2])  # Top 2 matches per term
        
        # Remove duplicates
        seen_concepts = set()
        filtered_matches = []
        for match in matches:
            if match["concept_id"] not in seen_concepts and match["confidence"] >= 0.75:
                seen_concepts.add(match["concept_id"])
                filtered_matches.append(match)
        
        return filtered_matches[:5]  # Allow more matches
    
    def _is_relevant_snomed_match(self, term: str, snomed_data: Dict) -> bool:
        """Check if a SNOMED match is relevant"""
        term_lower = term.lower()
        
        # Skip very generic terms
        if term_lower in ['pain', 'condition', 'disease', 'disorder', 'syndrome']:
            return False
        
        # Ensure the term is medically relevant
        medical_indicators = [
            'hypertension', 'diabetes', 'chest', 'heart', 'blood', 'pressure',
            'medication', 'drug', 'treatment', 'therapy', 'diagnosis'
        ]
        
        if any(indicator in term_lower for indicator in medical_indicators):
            return True
        
        # Check if it's a specific medical condition
        if len(term) >= 6 and any(char.isalpha() for char in term):
            return True
        
        return False
    
    async def _store_code_assignments(
        self, 
        note_id: str, 
        code_matches: Dict[str, List[Dict[str, Any]]]
    ):
        """Store code assignments in database"""
        try:
            with SessionLocal() as db:
                # Clear existing assignments for this note
                db.query(MedicalCodeAssignment).filter(
                    MedicalCodeAssignment.medical_note_id == note_id
                ).delete()
                
                assignments = []
                
                # Store ICD code assignments
                for icd_match in code_matches.get("icd_codes", []):
                    try:
                        # Find the ICD code in database
                        icd_code = db.query(ICDCode).filter(
                            ICDCode.code == icd_match["code"]
                        ).first()
                        
                        if icd_code:
                            assignment = MedicalCodeAssignment(
                                medical_note_id=note_id,
                                icd_code_id=icd_code.id,
                                confidence_score=icd_match.get("confidence", 0.0),
                                section=icd_match.get("section", "assessment")
                            )
                            assignments.append(assignment)
                    except Exception as e:
                        logger.warning(f"Error storing ICD assignment: {e}")
                        continue
                
                # Store CPT code assignments
                for cpt_match in code_matches.get("cpt_codes", []):
                    try:
                        # Find the CPT code in database
                        cpt_code = db.query(CPTCode).filter(
                            CPTCode.code == cpt_match["code"]
                        ).first()
                        
                        if cpt_code:
                            assignment = MedicalCodeAssignment(
                                medical_note_id=note_id,
                                cpt_code_id=cpt_code.id,
                                confidence_score=cpt_match.get("confidence", 0.0),
                                section=cpt_match.get("section", "plan")
                            )
                            assignments.append(assignment)
                    except Exception as e:
                        logger.warning(f"Error storing CPT assignment: {e}")
                        continue
                
                # Store SNOMED code assignments
                for snomed_match in code_matches.get("snomed_codes", []):
                    try:
                        # Find the SNOMED code in database
                        snomed_code = db.query(SNOMEDCode).filter(
                            SNOMEDCode.concept_id == snomed_match["code"]
                        ).first()
                        
                        if snomed_code:
                            assignment = MedicalCodeAssignment(
                                medical_note_id=note_id,
                                snomed_code_id=snomed_code.id,
                                confidence_score=snomed_match.get("confidence", 0.0),
                                section=snomed_match.get("section", "assessment")
                            )
                            assignments.append(assignment)
                    except Exception as e:
                        logger.warning(f"Error storing SNOMED assignment: {e}")
                        continue
                
                # Bulk insert assignments
                if assignments:
                    db.add_all(assignments)
                    db.commit()
                    logger.info(f"Stored {len(assignments)} code assignments for note {note_id}")
                else:
                    logger.info(f"No valid code assignments found for note {note_id}")
                
        except Exception as e:
            logger.error(f"Error storing code assignments: {e}")
            # Don't raise the exception - just log it so the API doesn't fail
    
    async def search_codes(
        self, 
        query: str, 
        code_type: str = "all",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search medical codes by query"""
        try:
            results = []
            
            if code_type in ["all", "icd"]:
                # Search ICD codes
                for icd_id, icd_data in list(self.icd_cache.items())[:1000]:  # Limit search scope
                    score = fuzz.partial_ratio(query.lower(), icd_data["description"])
                    if score >= 60:  # Lower threshold for search
                        results.append({
                            "type": "icd",
                            "id": icd_id,
                            "code": icd_data["code"],
                            "description": icd_data["description"],
                            "score": score
                        })
            
            if code_type in ["all", "cpt"]:
                # Search CPT codes
                for cpt_id, cpt_data in list(self.cpt_cache.items())[:1000]:
                    score = fuzz.partial_ratio(query.lower(), cpt_data["description"])
                    if score >= 60:
                        results.append({
                            "type": "cpt",
                            "id": cpt_id,
                            "code": cpt_data["code"],
                            "description": cpt_data["description"],
                            "score": score
                        })
            
            if code_type in ["all", "snomed"]:
                # Search SNOMED codes
                for snomed_id, snomed_data in list(self.snomed_cache.items())[:1000]:
                    score = max(
                        fuzz.partial_ratio(query.lower(), snomed_data["fsn"]),
                        fuzz.partial_ratio(query.lower(), snomed_data["pt"])
                    )
                    if score >= 60:
                        results.append({
                            "type": "snomed",
                            "id": snomed_id,
                            "concept_id": snomed_data["concept_id"],
                            "fsn": snomed_data["fsn"],
                            "pt": snomed_data["pt"],
                            "score": score
                        })
            
            # Sort by score and return top results
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching codes: {e}")
            return [] 