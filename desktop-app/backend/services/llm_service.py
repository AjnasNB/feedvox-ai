"""
LLM Service for Medical Note Extraction using AnythingLLM
"""

import requests
import httpx
import yaml
import json
import logging
import re
from typing import Dict, Any, Optional
import time

logger = logging.getLogger(__name__)

class LLMService:
    """LLM service for medical note extraction using AnythingLLM"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize LLM service with configuration"""
        self.api_key = "2ZKN48Y-F1M4D6T-GBX3F4K-DQFMEP7"
        self.base_url = "http://localhost:3001/api/v1"
        self.workspace_slug = "qc"
        self.stream = False
        self.timeout = 60
        
        self.chat_url = f"{self.base_url}/workspace/{self.workspace_slug}/chat"
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        logger.info(f"LLM service initialized for workspace: {self.workspace_slug}")
    
    async def extract_medical_note(
        self, 
        transcript: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract structured medical note from transcript using LLM"""
        
        if not session_id:
            session_id = f"medical-extraction-{int(time.time())}"
        
        logger.info(f"Starting medical note extraction from transcript: {transcript[:100]}...")
        
        # Try LLM first, then fallback to pattern extraction
        try:
            # Test connection first
            connection_ok = await self.test_connection()
            if not connection_ok:
                logger.warning("LLM service not available, using pattern extraction")
                return self._extract_with_patterns(transcript)
            
            # Create medical extraction prompt
            prompt = self._create_extraction_prompt(transcript)
            
            # Send to LLM
            response = await self._chat(prompt, session_id)
            
            if not response or len(response.strip()) < 10:
                logger.warning("Empty or too short LLM response, using pattern extraction")
                return self._extract_with_patterns(transcript)
            
            # Parse the JSON response
            medical_note = self._parse_json_response(response)
            
            if medical_note:
                logger.info("Medical note extraction successful")
                return {
                    "success": True,
                    "medical_note": medical_note,
                    "raw_response": response,
                    "session_id": session_id
                }
            else:
                logger.warning("Failed to parse medical note from LLM response, using pattern extraction")
                return self._extract_with_patterns(transcript)
                
        except Exception as e:
            logger.error(f"Error in LLM extraction: {e}, using pattern extraction")
            return self._extract_with_patterns(transcript)
    
    def _extract_with_patterns(self, transcript: str) -> Dict[str, Any]:
        """Extract medical data using pattern matching as fallback"""
        logger.info("Using pattern-based extraction")
        
        # Simple pattern-based extraction
        medical_note = {
            "chief_complaint": self._extract_chief_complaint(transcript),
            "history_present_illness": self._extract_hpi(transcript),
            "past_medical_history": self._extract_pmh(transcript),
            "medications": self._extract_medications(transcript),
            "allergies": self._extract_allergies(transcript),
            "social_history": self._extract_social_history(transcript),
            "family_history": self._extract_family_history(transcript),
            "vital_signs": self._extract_vital_signs(transcript),
            "physical_exam": self._extract_physical_exam(transcript),
            "assessment": self._extract_assessment(transcript),
            "plan": self._extract_plan(transcript)
        }
        
        return {
            "success": True,
            "medical_note": medical_note,
            "raw_response": f"Pattern extraction from: {transcript}",
            "session_id": f"pattern-{int(time.time())}"
        }
    
    def _extract_chief_complaint(self, text: str) -> str:
        """Extract chief complaint from text"""
        patterns = [
            r"(?:patient|pt)\s+(?:complains?|reports?|presents?)\s+(?:of|with)\s+([^.]{10,100})",
            r"(?:chief complaint|cc)[:]\s*([^.]{5,100})",
            r"presents?\s+with\s+([^.]{5,100})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).strip().capitalize()
        
        # Look for common symptoms
        if "chest pain" in text.lower():
            return "Chest pain"
        elif "headache" in text.lower():
            return "Headache"
        elif "fever" in text.lower():
            return "Fever"
        
        return "Not documented"
    
    def _extract_hpi(self, text: str) -> str:
        """Extract history of present illness"""
        # Look for timeline and description
        timeline_patterns = [
            r"(?:started|began|onset)\s+(\d+\s+(?:days?|weeks?|months?)\s+ago)",
            r"for\s+(\d+\s+(?:days?|weeks?|months?))",
            r"since\s+(\d+\s+(?:days?|weeks?|months?)\s+ago)",
            r"(\d+\s+(?:days?|weeks?|months?))\s+ago"
        ]
        
        timeline = ""
        for pattern in timeline_patterns:
            match = re.search(pattern, text.lower())
            if match:
                timeline = match.group(1)
                break
        
        # Look for descriptions and characteristics
        desc_patterns = [
            r"(?:pain|symptoms?)\s+(?:is|are)\s+described\s+as\s+([^.]{5,100})",
            r"(?:described|described as)\s+([^.]{5,100})",
            r"(?:pain|discomfort|symptoms?)\s+(?:that|which)\s+([^.]{10,150})",
            r"(?:chest pain|headache|symptoms?)\s+([^.]{10,150}(?:breathing|exertion|movement|rest))",
            r"(?:sharp|dull|aching|burning|stabbing|crushing)\s+([^.]{5,100})",
            r"(?:occurs|happens|gets worse|improves)\s+(?:with|during|when)\s+([^.]{5,100})"
        ]
        
        descriptions = []
        for pattern in desc_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if len(match.strip()) > 5:
                    descriptions.append(match.strip())
        
        # Look for associated symptoms
        symptom_patterns = [
            r"(?:associated with|along with|accompanied by)\s+([^.]{5,100})",
            r"(?:also has|also experiences|reports)\s+([^.]{5,100})",
            r"(?:shortness of breath|nausea|dizziness|sweating|fatigue)"
        ]
        
        symptoms = []
        for pattern in symptom_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, str) and len(match) > 3:
                    symptoms.append(match.strip())
        
        # Combine information
        hpi_parts = []
        if timeline:
            hpi_parts.append(f"Symptoms started {timeline}")
        
        if descriptions:
            unique_desc = list(dict.fromkeys(descriptions))  # Remove duplicates
            hpi_parts.append(f"described as {', '.join(unique_desc[:2])}")
        
        if symptoms:
            hpi_parts.append(f"associated with {', '.join(symptoms[:2])}")
        
        if hpi_parts:
            return ". ".join(hpi_parts).capitalize() + "."
        
        # Fallback - look for any pain or symptom description
        pain_desc = re.search(r"(chest pain|pain|symptoms?)\s+([^.]{20,200})", text.lower())
        if pain_desc:
            return f"Patient reports {pain_desc.group(0).strip()}."
        
        return "Not documented"
    
    def _extract_pmh(self, text: str) -> str:
        """Extract past medical history"""
        conditions = []
        
        # Common conditions
        condition_patterns = [
            r"\b(hypertension|high blood pressure)\b",
            r"\b(diabetes|diabetes mellitus)\b",
            r"\b(heart disease|cardiac disease)\b",
            r"\b(asthma|copd)\b"
        ]
        
        for pattern in condition_patterns:
            if re.search(pattern, text.lower()):
                match = re.search(pattern, text.lower())
                if match:
                    conditions.append(match.group(1))
        
        if conditions:
            return ", ".join(conditions).capitalize()
        
        return "Not documented"
    
    def _extract_medications(self, text: str) -> str:
        """Extract current medications"""
        # Enhanced medication patterns
        med_patterns = [
            r"(?:takes?|taking|on|prescribed|using)\s+([a-zA-Z]+(?:pril|statin|formin|zole|pine|lol|ide|mycin|cillin)\s+\d+\s*mg\s+(?:daily|twice daily|once daily|bid|tid))",
            r"([a-zA-Z]+(?:pril|statin|formin|zole|pine|lol|ide|mycin|cillin))\s+(\d+\s*mg)\s+(daily|twice daily|once daily|bid|tid)",
            r"(?:lisinopril|metformin|atorvastatin|omeprazole|hydrochlorothiazide|amlodipine|losartan|simvastatin)\s+\d+\s*mg\s+(?:daily|twice daily|once daily)",
            r"(\d+\s*mg)\s+(?:of\s+)?([a-zA-Z]+(?:pril|statin|formin|zole|pine|lol|ide))\s+(daily|twice daily|once daily)",
            r"([a-zA-Z]{4,})\s+(\d+\s*mg)\s+(daily|twice daily|once daily|bid|tid|qd)"
        ]
        
        medications = []
        text_lower = text.lower()
        
        # Common medication names to look for
        common_meds = [
            "lisinopril", "metformin", "atorvastatin", "omeprazole", "hydrochlorothiazide",
            "amlodipine", "losartan", "simvastatin", "aspirin", "ibuprofen", "acetaminophen"
        ]
        
        for med in common_meds:
            # Look for medication with dosage
            med_pattern = rf"{med}\s+(\d+\s*mg)\s+(daily|twice daily|once daily|bid|tid)"
            match = re.search(med_pattern, text_lower)
            if match:
                medications.append(f"{med.capitalize()} {match.group(1)} {match.group(2)}")
            elif med in text_lower:
                # Just the medication name without clear dosage
                medications.append(f"{med.capitalize()}")
        
        # Look for generic patterns
        for pattern in med_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 3:  # med, dose, frequency
                        med_name = match[0] if match[0] else match[1]
                        dose = match[1] if match[0] else match[0]
                        freq = match[2]
                        medications.append(f"{med_name.capitalize()} {dose} {freq}")
                    else:
                        medications.append(" ".join(match).strip().capitalize())
                else:
                    medications.append(match.strip().capitalize())
        
        if medications:
            # Remove duplicates and clean up
            unique_meds = []
            seen = set()
            for med in medications:
                med_clean = re.sub(r'\s+', ' ', med).strip()
                if med_clean.lower() not in seen and len(med_clean) > 3:
                    seen.add(med_clean.lower())
                    unique_meds.append(med_clean)
            
            return ", ".join(unique_meds[:5])  # Limit to 5 medications
        
        return "Not documented"
    
    def _extract_allergies(self, text: str) -> str:
        """Extract allergies"""
        if "no known allergies" in text.lower() or "nka" in text.lower() or "no allergies" in text.lower():
            return "No known allergies"
        
        allergy_patterns = [
            r"allergic to\s+([^.]{3,100})",
            r"allergies?[:]\s*([^.]{3,100})",
            r"allergy to\s+([^.]{3,100})",
            r"(?:penicillin|ibuprofen|aspirin|sulfa|latex|shellfish|nuts)\s*[,]?\s*([^.]{0,50}(?:rash|upset|reaction|swelling))",
            r"([a-zA-Z]+)\s+(?:gives me|causes|makes me)\s+([^.]{3,50})",
            r"can't take\s+([^.]{3,50})",
            r"adverse reaction to\s+([^.]{3,50})"
        ]
        
        allergies = []
        for pattern in allergy_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    # Combine drug and reaction
                    drug = match[0].strip()
                    reaction = match[1].strip() if len(match) > 1 and match[1] else ""
                    if drug and len(drug) > 2:
                        if reaction:
                            allergies.append(f"{drug} ({reaction})")
                        else:
                            allergies.append(drug)
                else:
                    allergy = match.strip()
                    if len(allergy) > 2:
                        allergies.append(allergy)
        
        if allergies:
            # Clean and format allergies
            clean_allergies = []
            for allergy in allergies[:3]:  # Limit to 3
                clean_allergy = re.sub(r'\s+', ' ', allergy).strip()
                clean_allergies.append(clean_allergy.capitalize())
            
            return ", ".join(clean_allergies)
        
        return "Not documented"
    
    def _extract_social_history(self, text: str) -> str:
        """Extract social history"""
        social_items = []
        
        # Smoking status
        smoking_patterns = [
            r"(non-smoker|doesn't smoke|never smoked|quit smoking)",
            r"(smoker|smokes|smoking|cigarettes)",
            r"(quit smoking|former smoker)\s+([^.]{5,50})"
        ]
        
        for pattern in smoking_patterns:
            match = re.search(pattern, text.lower())
            if match:
                smoking_status = match.group(1)
                if "non" in smoking_status or "doesn't" in smoking_status or "never" in smoking_status:
                    social_items.append("Non-smoker")
                elif "quit" in smoking_status or "former" in smoking_status:
                    social_items.append("Former smoker")
                else:
                    social_items.append("Smoker")
                break
        
        # Alcohol consumption
        alcohol_patterns = [
            r"drinks?\s+([^.]{5,100}(?:wine|beer|alcohol|glass|week|month|day)[^.]{0,50})",
            r"alcohol[:]\s*([^.]{5,100})",
            r"(socially|occasionally|rarely)\s+(?:drinks?|alcohol)",
            r"(\d+(?:-\d+)?)\s+(?:glasses?|drinks?|beers?)\s+(?:of\s+)?(?:wine|beer|alcohol)\s+(?:per\s+)?(week|month|day)",
            r"(?:about|approximately)\s+(\d+(?:-\d+)?)\s+(?:glasses?|drinks?)\s+([^.]{5,50})"
        ]
        
        for pattern in alcohol_patterns:
            match = re.search(pattern, text.lower())
            if match:
                alcohol_desc = match.group(0).strip()
                social_items.append(f"Alcohol: {alcohol_desc}")
                break
        
        # Exercise/Activity
        exercise_patterns = [
            r"exercise[s]?\s+([^.]{5,100})",
            r"(?:gym|workout|physical activity|walks?|runs?|jogs?)\s+([^.]{5,100})",
            r"(active|sedentary|exercises regularly|doesn't exercise)"
        ]
        
        for pattern in exercise_patterns:
            match = re.search(pattern, text.lower())
            if match:
                exercise_desc = match.group(0).strip()
                social_items.append(f"Exercise: {exercise_desc}")
                break
        
        # Occupation
        occupation_patterns = [
            r"(?:works? as|job|occupation|employed as)\s+([^.]{3,50})",
            r"(?:retired|unemployed|student|teacher|nurse|doctor|engineer)"
        ]
        
        for pattern in occupation_patterns:
            match = re.search(pattern, text.lower())
            if match:
                if isinstance(match.group(0), str):
                    social_items.append(f"Occupation: {match.group(0).strip()}")
                break
        
        if social_items:
            return ", ".join(social_items[:4])  # Limit to 4 items
        
        return "Not documented"
    
    def _extract_physical_exam(self, text: str) -> str:
        """Extract physical exam findings"""
        exam_patterns = [
            r"(?:physical exam|examination)\s+(?:reveals?|shows?)\s+([^.]{10,200})",
            r"(?:heart sounds?|cardiac exam)\s+(?:are|is|reveals?)?\s*([^.]{5,100})",
            r"(?:lung sounds?|pulmonary exam|chest exam)\s+(?:are|is|reveals?)?\s*([^.]{5,100})",
            r"(?:abdomen|abdominal exam)\s+(?:is|reveals?)?\s*([^.]{5,100})",
            r"(?:extremities|neurologic exam)\s+(?:are|is|reveals?)?\s*([^.]{5,100})",
            r"(?:blood pressure|bp|heart rate|pulse|temperature|temp)\s+(?:is|was|measures?)?\s*([^.]{3,50})",
            r"(?:normal|abnormal|clear|diminished|enlarged|tender|soft)\s+([^.]{5,100}(?:sounds?|exam|findings?))",
            r"(?:auscultation|palpation|inspection)\s+(?:reveals?|shows?)\s+([^.]{5,100})"
        ]
        
        findings = []
        for pattern in exam_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                finding = match.strip()
                if len(finding) > 5:
                    findings.append(finding)
        
        # Look for specific vital signs
        vital_patterns = [
            r"blood pressure\s+(\d+/\d+)",
            r"heart rate\s+(\d+)",
            r"temperature\s+(\d+\.?\d*)",
            r"pulse\s+(\d+)"
        ]
        
        vitals = []
        for pattern in vital_patterns:
            match = re.search(pattern, text.lower())
            if match:
                vitals.append(match.group(0))
        
        all_findings = findings + vitals
        if all_findings:
            # Clean and format findings
            clean_findings = []
            for finding in all_findings[:5]:  # Limit to 5 findings
                clean_finding = re.sub(r'\s+', ' ', finding).strip()
                clean_findings.append(clean_finding.capitalize())
            
            return ", ".join(clean_findings)
        
        return "Not documented"
    
    def _extract_assessment(self, text: str) -> str:
        """Extract clinical assessment"""
        assessment_patterns = [
            r"(?:assessment|diagnosis|impression|clinical impression)[:]\s*([^.]{10,200})",
            r"(?:likely|probably|appears to be|suggests?|consistent with|diagnosis of)\s+([^.]{5,150})",
            r"(?:working diagnosis|differential diagnosis|primary diagnosis)\s*[:]\s*([^.]{5,150})",
            r"(?:my assessment is|i think|i believe|it appears)\s+([^.]{10,150})",
            r"(?:this is|this appears to be|this looks like)\s+([^.]{5,150})"
        ]
        
        for pattern in assessment_patterns:
            match = re.search(pattern, text.lower())
            if match:
                assessment = match.group(1).strip()
                if len(assessment) > 5:
                    return assessment.capitalize()
        
        # Look for diagnostic terms
        diagnostic_terms = [
            "hypertension", "diabetes", "chest pain", "muscular pain", "cardiac", "non-cardiac",
            "gastritis", "reflux", "anxiety", "stress", "viral", "bacterial", "infection"
        ]
        
        found_terms = []
        for term in diagnostic_terms:
            if term in text.lower():
                found_terms.append(term)
        
        if found_terms:
            return f"Clinical findings suggest {', '.join(found_terms[:3])}"
        
        return "Not documented"
    
    def _extract_plan(self, text: str) -> str:
        """Extract treatment plan"""
        plan_patterns = [
            r"(?:plan|treatment plan|management plan)[:]\s*([^.]{10,300})",
            r"(?:recommend|prescribe|order|start|begin|continue)\s+([^.]{10,200})",
            r"(?:follow up|follow-up|return)\s+([^.]{5,100})",
            r"(?:will|plan to|going to|should)\s+([^.]{10,200})",
            r"(?:increase|decrease|adjust|change)\s+([^.]{10,150})",
            r"(?:monitor|check|test|lab work|blood work)\s+([^.]{5,100})"
        ]
        
        plan_items = []
        for pattern in plan_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                plan_item = match.strip()
                if len(plan_item) > 5:
                    plan_items.append(plan_item)
        
        if plan_items:
            # Clean and format plan items
            clean_plans = []
            for plan in plan_items[:4]:  # Limit to 4 plan items
                clean_plan = re.sub(r'\s+', ' ', plan).strip()
                clean_plans.append(clean_plan.capitalize())
            
            return ". ".join(clean_plans) + "."
        
        return "Not documented"
    
    def _create_extraction_prompt(self, transcript: str) -> str:
        """Create optimized prompt for medical note extraction"""
        return f"""You are a medical scribe AI. Extract structured medical information from this doctor-patient conversation transcript.

TRANSCRIPT:
{transcript}

Extract the information and return ONLY a clean JSON object with these exact fields:

{{
    "chief_complaint": "Brief statement of main complaint",
    "history_present_illness": "Detailed description of current symptoms with timeline",
    "past_medical_history": "Past medical conditions and surgeries as text",
    "medications": "Current medications with dosages as text",
    "allergies": "Drug and environmental allergies as text",
    "social_history": "Smoking, alcohol, occupation details as text",
    "family_history": "Family medical history as text",
    "vital_signs": "Vital signs mentioned or 'Not documented'",
    "physical_exam": "Physical examination findings as text or 'Not performed'",
    "assessment": "Clinical impression and working diagnosis as text",
    "plan": "Treatment plan and follow-up instructions as text"
}}

RULES:
1. Extract only information explicitly mentioned in the transcript
2. Use complete sentences, not fragments
3. For missing information, use 'Not documented'
4. Return ONLY the JSON object, no other text
5. Ensure all field values are properly quoted strings

JSON:"""
    
    async def _chat(self, message: str, session_id: str) -> str:
        """Send chat request to AnythingLLM"""
        data = {
            "message": message,
            "mode": "chat",
            "sessionId": session_id,
            "attachments": []
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.chat_url,
                    headers=self.headers,
                    json=data
                )
                response.raise_for_status()
                
                result = response.json()
                text_response = result.get('textResponse', '')
                
                logger.info(f"LLM response length: {len(text_response)}")
                return text_response
                
        except Exception as e:
            logger.error(f"Chat request failed: {e}")
            raise
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, str]]:
        """Parse JSON response from LLM"""
        try:
            # Clean the response
            response = response.strip()
            
            # Find JSON boundaries
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON found in response")
                return None
            
            json_str = response[start_idx:end_idx]
            
            # Clean up common JSON issues
            json_str = self._clean_json_string(json_str)
            
            # Parse JSON
            parsed = json.loads(json_str)
            
            # Validate and clean fields
            medical_note = {}
            required_fields = [
                "chief_complaint", "history_present_illness", "past_medical_history",
                "medications", "allergies", "social_history", "family_history",
                "vital_signs", "physical_exam", "assessment", "plan"
            ]
            
            for field in required_fields:
                value = parsed.get(field, "Not documented")
                if isinstance(value, str):
                    cleaned_value = self._clean_field_value(value)
                    medical_note[field] = cleaned_value
                else:
                    medical_note[field] = "Not documented"
            
            return medical_note
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            return None
    
    def _clean_json_string(self, json_str: str) -> str:
        """Clean JSON string to fix common formatting issues"""
        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Fix unescaped quotes in values
        json_str = re.sub(r'(?<!\\)"([^"]*)"([^",}\]]*)"', r'"\1\2"', json_str)
        
        return json_str
    
    def _clean_field_value(self, value: str) -> str:
        """Clean field values to remove artifacts and formatting issues"""
        if not value or not isinstance(value, str):
            return "Not documented"
        
        # Remove JSON artifacts
        artifacts = [
            '","close":false,"error":false}',
            '","close":true,"error":false}', 
            '"close":false,"error":false}',
            '"close":true,"error":false}',
            '"error":false}',
            '"error":true}',
            '","close":false',
            '","close":true',
            '"close":false',
            '"close":true'
        ]
        
        cleaned = value
        for artifact in artifacts:
            cleaned = cleaned.replace(artifact, '')
        
        # Remove JSON-like patterns
        cleaned = re.sub(r'[",{}:\[\]]+$', '', cleaned)
        cleaned = re.sub(r'^[",{}:\[\]]+', '', cleaned)
        
        # Remove close/error patterns
        cleaned = re.sub(r'[",]*close[",]*:\s*(true|false)[",]*', '', cleaned)
        cleaned = re.sub(r'[",]*error[",]*:\s*(true|false)[",]*', '', cleaned)
        
        # Clean whitespace
        cleaned = cleaned.strip()
        cleaned = cleaned.strip('",{}[]')
        cleaned = cleaned.strip()
        
        # Check if empty or too short
        if not cleaned or len(cleaned) < 3:
            return "Not documented"
        
        # Check for incomplete words
        if cleaned.lower().startswith(('ination', 'tion', 'sion', 'ment')):
            return "Not documented"
        
        return cleaned
    
    def _create_extraction_failure(self) -> Dict[str, Any]:
        """Create response for extraction failure"""
        return {
            "success": False,
            "medical_note": {
                "chief_complaint": "Not documented",
                "history_present_illness": "Not documented",
                "past_medical_history": "Not documented",
                "medications": "Not documented",
                "allergies": "Not documented",
                "social_history": "Not documented",
                "family_history": "Not documented",
                "vital_signs": "Not documented",
                "physical_exam": "Not documented",
                "assessment": "Not documented",
                "plan": "Not documented"
            },
            "raw_response": "",
            "session_id": ""
        }
    
    def _extract_family_history(self, text: str) -> str:
        """Extract family history"""
        family_patterns = [
            r"family history[^.]*[:]\s*([^.]{10,300})",
            r"(?:father|mother|parent|family)[^.]{0,100}(?:had|has|died of|history of)\s+([^.]{10,200})",
            r"(?:father|mother|parent)\s+([^.]{10,200}(?:disease|diabetes|hypertension|cancer|heart|stroke))",
            r"family history is significant for\s+([^.]{10,300})",
            r"(?:genetic|hereditary|familial)\s+(?:history|predisposition)\s*[:]\s*([^.]{10,200})"
        ]
        
        family_items = []
        for pattern in family_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                family_item = match.strip()
                if len(family_item) > 10:
                    family_items.append(family_item)
        
        # Look for specific family member conditions
        family_conditions = []
        
        # Father conditions
        father_patterns = [
            r"father[^.]{0,100}(coronary artery disease|heart disease|myocardial infarction|heart attack|diabetes|hypertension|cancer)",
            r"father[^.]{0,50}died[^.]{0,50}(at age \d+|age \d+)"
        ]
        
        for pattern in father_patterns:
            match = re.search(pattern, text.lower())
            if match:
                father_info = match.group(0).strip()
                family_conditions.append(f"Father: {father_info}")
        
        # Mother conditions
        mother_patterns = [
            r"mother[^.]{0,100}(diabetes|hypertension|heart disease|cancer|stroke)",
            r"mother[^.]{0,50}(still living|living at age \d+|age \d+)"
        ]
        
        for pattern in mother_patterns:
            match = re.search(pattern, text.lower())
            if match:
                mother_info = match.group(0).strip()
                family_conditions.append(f"Mother: {mother_info}")
        
        all_family = family_items + family_conditions
        if all_family:
            # Clean and format family history
            clean_family = []
            for item in all_family[:4]:  # Limit to 4 items
                clean_item = re.sub(r'\s+', ' ', item).strip()
                clean_family.append(clean_item.capitalize())
            
            return ". ".join(clean_family) + "."
        
        return "Not documented"
    
    def _extract_vital_signs(self, text: str) -> str:
        """Extract vital signs"""
        vital_patterns = [
            r"vital signs?[^.]*[:]\s*([^.]{10,300})",
            r"blood pressure\s+(\d+/\d+)",
            r"bp\s+(\d+/\d+)",
            r"heart rate\s+(\d+)",
            r"hr\s+(\d+)",
            r"pulse\s+(\d+)",
            r"temperature\s+(\d+\.?\d*\s*[fF]?)",
            r"temp\s+(\d+\.?\d*\s*[fF]?)",
            r"respiratory rate\s+(\d+)",
            r"rr\s+(\d+)",
            r"oxygen saturation\s+(\d+%)",
            r"o2 sat\s+(\d+%)",
            r"spo2\s+(\d+%)"
        ]
        
        vitals = []
        for pattern in vital_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                vital = match.strip()
                if len(vital) > 1:
                    vitals.append(vital)
        
        # Look for complete vital signs section
        vital_section_pattern = r"vital signs?[^.]*[:]\s*([^.]{20,500})"
        section_match = re.search(vital_section_pattern, text.lower())
        if section_match:
            vital_section = section_match.group(1).strip()
            if len(vital_section) > 20:
                return vital_section.capitalize()
        
        if vitals:
            # Format vital signs
            formatted_vitals = []
            for vital in vitals[:6]:  # Limit to 6 vital signs
                if re.match(r'\d+/\d+', vital):
                    formatted_vitals.append(f"BP {vital}")
                elif re.match(r'\d+\.?\d*\s*[fF]?', vital) and ('temp' in text.lower() or 'temperature' in text.lower()):
                    formatted_vitals.append(f"Temp {vital}")
                elif re.match(r'\d+', vital):
                    if 'heart rate' in text.lower() or 'hr' in text.lower():
                        formatted_vitals.append(f"HR {vital}")
                    elif 'respiratory' in text.lower() or 'rr' in text.lower():
                        formatted_vitals.append(f"RR {vital}")
                    else:
                        formatted_vitals.append(vital)
                elif '%' in vital:
                    formatted_vitals.append(f"O2 sat {vital}")
                else:
                    formatted_vitals.append(vital)
            
            return ", ".join(formatted_vitals)
        
        return "Not documented"
    
    async def test_connection(self) -> bool:
        """Test connection to LLM service"""
        try:
            response = await self._chat("Hello", "test-connection")
            return len(response) > 0
        except:
            return False
    

