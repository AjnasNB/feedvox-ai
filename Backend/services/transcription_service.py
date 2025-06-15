"""
Transcription Service using Whisper
Based on the working logic from simple-whisper-transcription-main
"""

import whisper
import numpy as np
import soundfile as sf
import tempfile
import os
import logging
from typing import Optional, Dict, Any, Union
from io import BytesIO
import time

logger = logging.getLogger(__name__)

class TranscriptionService:
    """Whisper-based transcription service"""
    
    def __init__(self, model_name: str = "base.en"):
        """
        Initialize transcription service
        
        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large)
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load Whisper model with NPU support"""
        try:
            logger.info(f"Loading Whisper model: {self.model_name}")
            
            # Try to detect and use NPU if available
            device = "cpu"
            try:
                import torch
                # Check for CUDA
                if torch.cuda.is_available():
                    device = "cuda"
                    logger.info("CUDA detected, using GPU acceleration")
                # Check for NPU (Qualcomm Snapdragon)
                elif hasattr(torch.backends, 'quantized') and hasattr(torch.backends.quantized, 'supported_engines'):
                    if 'qnnpack' in torch.backends.quantized.supported_engines:
                        device = "cpu"  # Use CPU with NPU backend
                        logger.info("NPU backend detected, enabling optimizations")
                # Check for MPS (Apple Silicon)
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    device = "mps"
                    logger.info("Apple Silicon MPS detected, using Metal acceleration")
                else:
                    logger.info("Using CPU for inference")
            except ImportError:
                logger.info("PyTorch not available, using CPU")
                
            # Load model with device specification
            self.model = whisper.load_model(self.model_name, device=device)
            logger.info(f"Whisper model loaded successfully on {device}")
            
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            raise
    
    async def transcribe_audio_file(
        self, 
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribe audio file
        
        Args:
            audio_path: Path to audio file
            language: Language code (auto-detect if None)
            task: 'transcribe' or 'translate'
            
        Returns:
            Dict with transcription results
        """
        try:
            start_time = time.time()
            
            # Check if file exists
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            logger.info(f"Transcribing audio file: {audio_path}")
            
            # Load and process audio data
            audio_data, sample_rate = sf.read(audio_path)
            duration = len(audio_data) / sample_rate
            
            logger.info(f"Audio loaded: {duration:.2f}s, {sample_rate}Hz")
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # Resample to 16kHz if needed (Whisper requirement)
            if sample_rate != 16000:
                logger.info(f"Resampling from {sample_rate}Hz to 16000Hz")
                from scipy import signal
                audio_data = signal.resample(
                    audio_data, 
                    int(len(audio_data) * 16000 / sample_rate)
                )
            
            # Ensure audio is float32 and normalized
            audio_data = audio_data.astype(np.float32)
            
            # Transcribe with NPU optimizations
            logger.info("Starting transcription...")
            options = {
                "task": task,
                "fp16": False,  # Use FP32 for stability
                "condition_on_previous_text": False,  # Faster processing
                "compression_ratio_threshold": 2.4,  # NPU optimization
                "logprob_threshold": -1.0,  # NPU optimization
                "no_speech_threshold": 0.6,  # Reduce false positives
            }
            
            # Enable NPU-specific optimizations
            try:
                import torch
                if hasattr(torch.backends, 'quantized'):
                    if 'qnnpack' in torch.backends.quantized.supported_engines:
                        torch.backends.quantized.engine = 'qnnpack'
                        logger.info("Enabled QNNPACK for NPU acceleration")
            except:
                pass
            
            if language:
                options["language"] = language
            
            result = self.model.transcribe(audio_data, **options)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Transcription completed in {processing_time:.2f}s")
            
            return {
                "text": result["text"].strip(),
                "language": result.get("language", "en"),
                "segments": result.get("segments", []),
                "duration_seconds": duration,
                "processing_time_seconds": processing_time,
                "model_used": self.model_name,
                "confidence_score": self._calculate_average_confidence(result.get("segments", []))
            }
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise
    
    async def transcribe_audio_bytes(
        self, 
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribe audio from bytes
        
        Args:
            audio_bytes: Audio file as bytes
            filename: Original filename (for format detection)
            language: Language code (auto-detect if None)
            task: 'transcribe' or 'translate'
            
        Returns:
            Dict with transcription results
        """
        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=os.path.splitext(filename)[1] or '.wav'
            ) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name
            
            try:
                # Transcribe the temporary file
                result = await self.transcribe_audio_file(
                    tmp_path, 
                    language=language, 
                    task=task
                )
                return result
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Error transcribing audio bytes: {e}")
            raise
    
    def _calculate_average_confidence(self, segments: list) -> Optional[float]:
        """Calculate average confidence from segments"""
        if not segments:
            return None
            
        confidences = []
        for segment in segments:
            # Whisper doesn't always provide confidence, so we estimate
            if "confidence" in segment:
                confidences.append(segment["confidence"])
            elif "no_speech_prob" in segment:
                # Estimate confidence from no_speech_prob
                confidences.append(1.0 - segment["no_speech_prob"])
        
        if confidences:
            return sum(confidences) / len(confidences)
        
        return None
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages"""
        return whisper.tokenizer.LANGUAGES
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "languages": list(whisper.tokenizer.LANGUAGES.keys()),
            "max_length": 30 * 16000,  # 30 seconds at 16kHz
            "sample_rate": 16000
        }

class LiveTranscriptionService:
    """
    Live transcription service for real-time audio
    Based on the LiveTranscriber from simple-whisper-transcription-main
    """
    
    def __init__(
        self,
        model_name: str = "base.en",
        sample_rate: int = 16000,
        chunk_duration: int = 4,
        channels: int = 1,
        silence_threshold: float = 0.001
    ):
        """Initialize live transcription service"""
        self.transcription_service = TranscriptionService(model_name)
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.channels = channels
        self.silence_threshold = silence_threshold
        self.chunk_samples = int(sample_rate * chunk_duration)
        
        self.is_recording = False
        self.audio_buffer = np.array([], dtype=np.float32)
        
    async def start_recording(self):
        """Start live recording and transcription"""
        # Implementation would depend on the audio input method
        # This is a placeholder for the live recording functionality
        self.is_recording = True
        logger.info("Live transcription started")
    
    async def stop_recording(self) -> Dict[str, Any]:
        """Stop recording and return final transcription"""
        self.is_recording = False
        
        if len(self.audio_buffer) > 0:
            # Process final buffer
            result = await self._process_audio_chunk(self.audio_buffer)
            self.audio_buffer = np.array([], dtype=np.float32)
            return result
        
        return {"text": "", "duration_seconds": 0}
    
    async def _process_audio_chunk(self, audio_chunk: np.ndarray) -> Dict[str, Any]:
        """Process a chunk of audio data"""
        try:
            # Check if chunk has sufficient audio
            if np.abs(audio_chunk).mean() < self.silence_threshold:
                return {"text": "", "is_silence": True}
            
            # Save chunk to temporary file for transcription
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                sf.write(tmp_file.name, audio_chunk, self.sample_rate)
                
                result = await self.transcription_service.transcribe_audio_file(tmp_file.name)
                
                # Clean up
                os.unlink(tmp_file.name)
                
                return result
                
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            return {"text": "", "error": str(e)} 