"""Audio generation service wrapping generate_standalone_speech functionality."""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import threading
import time

from script_to_speech.tts_providers.tts_provider_manager import TTSProviderManager
from script_to_speech.utils.generate_standalone_speech import (
    generate_standalone_speech, 
    _build_tts_provider_config_data,
    get_provider_class
)

from ..models import (
    GenerationRequest, TaskResponse, TaskStatus, TaskStatusResponse, 
    GenerationResult
)
from ..config import settings
from .voice_library_service import voice_library_service

logger = logging.getLogger(__name__)


class GenerationTask:
    """Represents an audio generation task."""
    
    def __init__(self, task_id: str, request: GenerationRequest):
        self.task_id = task_id
        self.request = request
        self.status = TaskStatus.PENDING
        self.progress = 0.0
        self.message = "Task created"
        self.result: Optional[GenerationResult] = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None


class GenerationService:
    """Service for managing audio generation tasks."""
    
    def __init__(self) -> None:
        """Initialize the generation service."""
        self._tasks: Dict[str, GenerationTask] = {}
        self._executor = None
        self._lock = threading.Lock()
    
    async def create_generation_task(self, request: GenerationRequest) -> TaskResponse:
        """Create a new audio generation task."""
        task_id = str(uuid.uuid4())
        task = GenerationTask(task_id, request)
        
        with self._lock:
            self._tasks[task_id] = task
        
        # Start the generation in the background
        asyncio.create_task(self._process_generation_task(task))
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Generation task created"
        )
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatusResponse]:
        """Get the status of a generation task."""
        with self._lock:
            task = self._tasks.get(task_id)
        
        if not task:
            return None
        
        result_dict = None
        if task.result:
            result_dict = task.result.dict()
        
        return TaskStatusResponse(
            task_id=task_id,
            status=task.status,
            message=task.message,
            progress=task.progress,
            result=result_dict,
            error=task.error
        )
    
    def get_all_tasks(self) -> List[TaskStatusResponse]:
        """Get status of all tasks."""
        with self._lock:
            tasks = list(self._tasks.values())
        
        return [
            TaskStatusResponse(
                task_id=task.task_id,
                status=task.status,
                message=task.message,
                progress=task.progress,
                result=task.result.dict() if task.result else None,
                error=task.error
            )
            for task in tasks
        ]
    
    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed tasks."""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        removed_count = 0
        
        with self._lock:
            task_ids_to_remove = []
            for task_id, task in self._tasks.items():
                if (task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED) and
                    task.created_at.timestamp() < cutoff_time):
                    task_ids_to_remove.append(task_id)
            
            for task_id in task_ids_to_remove:
                del self._tasks[task_id]
                removed_count += 1
        
        return removed_count
    
    async def _process_generation_task(self, task: GenerationTask) -> None:
        """Process a generation task in the background."""
        try:
            # Update task status
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.utcnow()
            task.message = "Starting audio generation"
            task.progress = 0.1
            
            logger.info(f"Starting generation task {task.task_id}")
            
            # Build configuration
            config = await self._build_generation_config(task)
            task.progress = 0.2
            task.message = "Configuration built"
            
            # Create TTS provider manager
            tts_manager = TTSProviderManager(
                config_data=config,
                overall_provider=None,
                dummy_tts_provider_override=False
            )
            task.progress = 0.3
            task.message = "TTS provider initialized"
            
            # Generate audio files
            generated_files = await self._generate_audio_files(task, tts_manager)
            task.progress = 0.9
            task.message = "Audio generation completed"
            
            # Create result
            task.result = GenerationResult(
                files=generated_files,
                provider=task.request.provider,
                voice_id=self._extract_voice_id(task.request),
                text_preview=task.request.text[:50] + "..." if len(task.request.text) > 50 else task.request.text,
                duration_ms=None  # Could be calculated if needed
            )
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.progress = 1.0
            task.message = f"Generated {len(generated_files)} audio file(s)"
            
            logger.info(f"Completed generation task {task.task_id}")
            
        except Exception as e:
            logger.error(f"Error in generation task {task.task_id}: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task.error = str(e)
            task.message = f"Generation failed: {str(e)}"
    
    async def _build_generation_config(self, task: GenerationTask) -> Dict[str, Any]:
        """Build TTS provider configuration for the task."""
        request = task.request
        
        # Create a mock argparse.Namespace object for _build_tts_provider_config_data
        class MockArgs:
            def __init__(self, provider: str, config: Dict[str, Any], sts_id: Optional[str]):
                self.provider = provider
                self.sts_id = sts_id
                # Add all config items as attributes
                for key, value in config.items():
                    setattr(self, key, value)
        
        # If sts_id is provided, expand it using voice library
        config = request.config.copy()
        if request.sts_id:
            try:
                expanded_config = voice_library_service.expand_sts_id(
                    request.provider, request.sts_id
                )
                # Merge expanded config with provided overrides
                for key, value in config.items():
                    expanded_config[key] = value
                config = expanded_config
            except Exception as e:
                logger.warning(f"Failed to expand sts_id {request.sts_id}: {e}")
        
        # Create mock args
        mock_args = MockArgs(request.provider, config, request.sts_id)
        
        # Get provider class
        provider_class = get_provider_class(request.provider)
        
        # Build config using existing function
        return _build_tts_provider_config_data(mock_args, provider_class)
    
    async def _generate_audio_files(
        self, 
        task: GenerationTask, 
        tts_manager: TTSProviderManager
    ) -> List[str]:
        """Generate audio files using the TTS manager."""
        generated_files = []
        request = task.request
        
        # Run generation in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        for variant in range(1, request.variants + 1):
            try:
                # Update progress
                progress = 0.3 + (0.6 * variant / request.variants)
                task.progress = progress
                task.message = f"Generating variant {variant}/{request.variants}"
                
                # Generate audio in thread
                def generate_audio():
                    generate_standalone_speech(
                        tts_manager=tts_manager,
                        text=request.text,
                        variant_num=variant if request.variants > 1 else 1,
                        output_dir=str(settings.AUDIO_OUTPUT_DIR),
                        split_audio=False,  # Keep simple for GUI
                        output_filename=request.output_filename
                    )
                
                await loop.run_in_executor(None, generate_audio)
                
                # Find the generated file
                generated_file = self._find_generated_file(
                    request, variant, tts_manager
                )
                if generated_file:
                    generated_files.append(generated_file)
                
            except Exception as e:
                logger.error(f"Failed to generate variant {variant}: {e}")
                # Continue with other variants
        
        if not generated_files:
            raise RuntimeError("No audio files were generated successfully")
        
        return generated_files
    
    def _find_generated_file(
        self, 
        request: GenerationRequest, 
        variant: int, 
        tts_manager: TTSProviderManager
    ) -> Optional[str]:
        """Find the generated audio file."""
        try:
            # Build expected filename similar to generate_standalone_speech
            from script_to_speech.utils.generate_standalone_speech import clean_filename
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            text_preview = clean_filename(request.text[:30])
            variant_suffix = f"_variant{variant}" if request.variants > 1 else ""
            
            provider_id = tts_manager.get_provider_identifier("default")
            voice_id = tts_manager.get_speaker_identifier("default")
            
            if request.output_filename:
                filename = f"{request.output_filename}{variant_suffix}.mp3"
            else:
                filename = f"{provider_id}--{voice_id}--{text_preview}{variant_suffix}--{timestamp}.mp3"
            
            file_path = settings.AUDIO_OUTPUT_DIR / filename
            
            # Check if file exists (with some tolerance for timing)
            for _ in range(10):  # Try for up to 1 second
                if file_path.exists():
                    return filename
                time.sleep(0.1)
            
            # If not found, try to find any recent file
            recent_files = [
                f for f in settings.AUDIO_OUTPUT_DIR.glob("*.mp3")
                if f.stat().st_mtime > time.time() - 30  # Last 30 seconds
            ]
            
            if recent_files:
                # Return the most recent file
                recent_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                return recent_files[0].name
            
        except Exception as e:
            logger.error(f"Error finding generated file: {e}")
        
        return None
    
    def _extract_voice_id(self, request: GenerationRequest) -> str:
        """Extract voice identifier from request."""
        if request.sts_id:
            return request.sts_id
        
        # Try common voice field names
        for field_name in ["voice", "voice_id", "default_voice_name"]:
            if field_name in request.config:
                return str(request.config[field_name])
        
        return "unknown"


# Global instance
generation_service = GenerationService()