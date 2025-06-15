"""
Service Manager for FeedVox AI
Handles configuration, service initialization, and data flow coordination
"""

import logging
import os
import yaml
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from services.llm_service import LLMService
from services.medical_coding_service import MedicalCodingService
from services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)

class ServiceManager:
    """Centralized service manager for FeedVox AI"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize service manager with configuration"""
        self.config_path = config_path
        self.config = self._load_configuration()
        self.services = {}
        self._initialize_services()
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from file with environment variable override"""
        try:
            config_path = Path(self.config_path)
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {config_path}")
            else:
                logger.warning(f"Config file {config_path} not found, using defaults")
                config = self._get_default_configuration()
            
            # Override with environment variables
            config = self._apply_environment_overrides(config)
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return self._get_default_configuration()
    
    def _get_default_configuration(self) -> Dict[str, Any]:
        """Get default configuration when no config file exists"""
        return {
            "api_key": None,
            "llm": {
                "base_url": "http://localhost:3001/api/v1",
                "workspace_slug": "medical",
                "timeout": 60,
                "stream": False
            },
            "medical_coding": {
                "confidence_threshold": 0.75,
                "max_codes_per_type": 5,
                "enable_fuzzy_matching": True
            },
            "audio": {
                "sample_rate": 16000,
                "chunk_duration": 4.0,
                "language": "en",
                "model_size": "base.en"
            }
        }
    
    def _apply_environment_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration"""
        # API Key
        api_key = os.getenv("ANYTHINGLLM_API_KEY") or os.getenv("LLM_API_KEY")
        if api_key:
            config["api_key"] = api_key
        
        # LLM Configuration
        llm_config = config.setdefault("llm", {})
        if os.getenv("ANYTHINGLLM_BASE_URL"):
            llm_config["base_url"] = os.getenv("ANYTHINGLLM_BASE_URL")
        if os.getenv("ANYTHINGLLM_WORKSPACE"):
            llm_config["workspace_slug"] = os.getenv("ANYTHINGLLM_WORKSPACE")
        
        # Medical Coding Configuration
        medical_config = config.setdefault("medical_coding", {})
        if os.getenv("MEDICAL_CODING_CONFIDENCE_THRESHOLD"):
            medical_config["confidence_threshold"] = float(os.getenv("MEDICAL_CODING_CONFIDENCE_THRESHOLD"))
        
        # Database Configuration
        if os.getenv("DATABASE_URL"):
            config.setdefault("database", {})["url"] = os.getenv("DATABASE_URL")
        
        return config
    
    def _initialize_services(self):
        """Initialize all services with current configuration"""
        try:
            # Initialize LLM Service
            self.services["llm"] = LLMService(self.config_path)
            if self.config.get("api_key"):
                self.services["llm"].update_config(api_key=self.config["api_key"])
            
            # Initialize Medical Coding Service
            self.services["medical_coding"] = MedicalCodingService(self.config_path)
            
            # Initialize Transcription Service if available
            try:
                self.services["transcription"] = TranscriptionService(self.config)
            except ImportError:
                logger.warning("Transcription service not available")
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get service instance by name"""
        return self.services.get(service_name)
    
    def update_configuration(self, updates: Dict[str, Any]) -> bool:
        """Update configuration and reinitialize affected services"""
        try:
            # Update configuration
            for key, value in updates.items():
                if "." in key:
                    # Handle nested keys like "llm.api_key"
                    sections = key.split(".")
                    current = self.config
                    for section in sections[:-1]:
                        current = current.setdefault(section, {})
                    current[sections[-1]] = value
                else:
                    self.config[key] = value
            
            # Update services with new configuration
            self._update_services(updates)
            
            # Save configuration to file
            self._save_configuration()
            
            logger.info(f"Configuration updated: {list(updates.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return False
    
    def _update_services(self, updates: Dict[str, Any]):
        """Update services with new configuration"""
        llm_updates = {}
        medical_updates = {}
        
        for key, value in updates.items():
            if key.startswith("llm."):
                service_key = key.replace("llm.", "")
                llm_updates[service_key] = value
            elif key.startswith("medical_coding."):
                service_key = key.replace("medical_coding.", "")
                medical_updates[service_key] = value
            elif key == "api_key":
                llm_updates["api_key"] = value
        
        # Update LLM service
        if llm_updates and "llm" in self.services:
            self.services["llm"].update_config(**llm_updates)
        
        # Update Medical Coding service
        if medical_updates and "medical_coding" in self.services:
            self.services["medical_coding"].update_config(**medical_updates)
    
    def _save_configuration(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    async def process_medical_transcription(
        self, 
        transcript: str,
        session_id: Optional[str] = None,
        include_coding: bool = True
    ) -> Dict[str, Any]:
        """
        Process medical transcription through the complete pipeline
        
        Args:
            transcript: Medical conversation transcript
            session_id: Optional session ID for tracking
            include_coding: Whether to include medical coding
            
        Returns:
            Complete processing results
        """
        results = {
            "success": False,
            "transcript": transcript,
            "session_id": session_id,
            "medical_note": {},
            "medical_codes": {},
            "processing_time": 0
        }
        
        import time
        start_time = time.time()
        
        try:
            # Extract medical note using LLM service
            llm_service = self.get_service("llm")
            if llm_service:
                note_result = await llm_service.extract_medical_note(transcript, session_id)
                results["medical_note"] = note_result.get("medical_note", {})
                results["success"] = note_result.get("success", False)
                results["session_id"] = note_result.get("session_id", session_id)
                
                # Generate medical codes if extraction was successful
                if include_coding and results["success"] and results["medical_note"]:
                    coding_service = self.get_service("medical_coding")
                    if coding_service:
                        # Create a temporary note ID for coding
                        import uuid
                        temp_note_id = str(uuid.uuid4())
                        
                        coding_result = await coding_service.code_medical_note(
                            results["medical_note"], 
                            temp_note_id
                        )
                        results["medical_codes"] = coding_result
            
            results["processing_time"] = time.time() - start_time
            logger.info(f"Medical transcription processed in {results['processing_time']:.2f}s")
            
        except Exception as e:
            logger.error(f"Error processing medical transcription: {e}")
            results["error"] = str(e)
            results["processing_time"] = time.time() - start_time
        
        return results
    
    async def test_services(self) -> Dict[str, bool]:
        """Test all services and return their status"""
        status = {}
        
        # Test LLM service
        llm_service = self.get_service("llm")
        if llm_service:
            try:
                status["llm"] = await llm_service.test_connection()
            except Exception as e:
                logger.error(f"LLM service test failed: {e}")
                status["llm"] = False
        else:
            status["llm"] = False
        
        # Test Medical Coding service
        coding_service = self.get_service("medical_coding")
        if coding_service:
            try:
                # Test by searching for a common term
                results = await coding_service.search_codes("hypertension", limit=1)
                status["medical_coding"] = len(results) > 0
            except Exception as e:
                logger.error(f"Medical coding service test failed: {e}")
                status["medical_coding"] = False
        else:
            status["medical_coding"] = False
        
        # Test Transcription service
        transcription_service = self.get_service("transcription")
        status["transcription"] = transcription_service is not None
        
        return status
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration (excluding sensitive data)"""
        safe_config = self.config.copy()
        
        # Remove sensitive information
        if "api_key" in safe_config:
            safe_config["api_key"] = "***" if safe_config["api_key"] else None
        
        return safe_config
    
    def get_service_status(self) -> Dict[str, str]:
        """Get status of all services"""
        return {
            name: "initialized" if service else "not_available"
            for name, service in self.services.items()
        }


# Global service manager instance
service_manager = None

def get_service_manager(config_path: str = "config.yaml") -> ServiceManager:
    """Get or create global service manager instance"""
    global service_manager
    if service_manager is None:
        service_manager = ServiceManager(config_path)
    return service_manager

def initialize_services(config_path: str = "config.yaml") -> ServiceManager:
    """Initialize services with configuration"""
    global service_manager
    service_manager = ServiceManager(config_path)
    return service_manager 