import concurrent.futures
import io
import logging
import sys
import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from pydub import AudioSegment
from tqdm import tqdm

from ..tts_providers.base.exceptions import TTSError, TTSRateLimitError
from ..tts_providers.tts_provider_manager import TTSProviderManager
from ..utils.logging import get_screenplay_logger
from .models import AudioClipInfo, AudioGenerationTask, ReportingState, TaskStatus
from .reporting import print_audio_task_details
from .utils import check_audio_level, check_audio_silence

# Get logger for this module
logger = get_screenplay_logger("audio_generation.download_manager")

MAX_BACKOFF_SECONDS = 120.0


class AudioDownloadManager:
    """
    Manages the audio download process with provider-specific concurrency limits,
    rate limit handling, backoff, and retry logic.
    """

    def __init__(
        self,
        tasks: List[AudioGenerationTask],
        tts_provider_manager: TTSProviderManager,
        global_max_workers: int = 12,
        initial_backoff_seconds: float = 10.0,
        backoff_factor: float = 2.0,
        max_retries: int = 3,
        silence_threshold: Optional[float] = None,
    ):
        """
        Initialize the download manager.

        Args:
            tasks: List of audio generation tasks to process
            tts_provider_manager: Manager to communicate with TTS providers
            global_max_workers: Global maximum number of concurrent workers
            initial_backoff_seconds: Initial backoff time when rate limited (in seconds)
            backoff_factor: Factor to multiply backoff time by on each retry
            max_retries: Maximum number of times to retry a rate-limited task
            silence_threshold: dBFS threshold for detecting silence
        """
        self.tasks = tasks
        self.tts_provider_manager = tts_provider_manager
        self.global_max_workers = global_max_workers
        self.initial_backoff_seconds = initial_backoff_seconds
        self.backoff_factor = backoff_factor
        self.max_retries = max_retries
        self.silence_threshold = silence_threshold

        # Initialize concurrency management
        self.global_semaphore = threading.Semaphore(global_max_workers)
        self.provider_semaphores: Dict[str, threading.Semaphore] = {}

        # Initialize provider rate limit state
        self.provider_rate_limited: Dict[str, bool] = defaultdict(bool)
        self.provider_backoff_until: Dict[str, float] = defaultdict(float)
        self.provider_backoff_time: Dict[str, float] = defaultdict(
            lambda: initial_backoff_seconds
        )
        # Track when we last hit rate limits for conservative backoff reset
        self.provider_last_rate_limit_time: Dict[str, float] = defaultdict(float)

        # Initialize task tracking
        self.pending_tasks: List[AudioGenerationTask] = []
        self.completed_tasks: List[AudioGenerationTask] = []
        self.rate_limited_tasks: Dict[str, List[AudioGenerationTask]] = defaultdict(
            list
        )

        # Result tracking
        self.reporting_state = ReportingState()

        # Thread locks
        self.state_lock = threading.RLock()  # For thread-safe state updates

        # Set up provider-specific semaphores
        self._setup_provider_semaphores()

    def _setup_provider_semaphores(self) -> None:
        """Initialize semaphores for each provider based on their recommended thread limits."""
        # First, identify all unique providers in the task list
        providers: Set[str] = set()
        for task in self.tasks:
            if task.provider_id:
                providers.add(task.provider_id)

        # Create semaphores for each provider
        for provider in providers:
            try:
                # Get the provider's recommended thread limit
                thread_limit = (
                    self.tts_provider_manager.get_max_provider_download_threads(
                        provider
                    )
                )
                # Create a semaphore with that limit
                self.provider_semaphores[provider] = threading.Semaphore(thread_limit)
                logger.info(
                    f"Provider '{provider}' configured with {thread_limit} concurrent threads"
                )
            except Exception as e:
                # If there's an error, use a conservative default of 1
                logger.error(
                    f"Error getting thread limit for provider '{provider}': {e}"
                )
                self.provider_semaphores[provider] = threading.Semaphore(1)
                logger.info(f"Provider '{provider}' defaulting to 1 concurrent thread")

    def _can_process_task(self, task: AudioGenerationTask) -> bool:
        """
        Check if a task can be processed now based on rate limit state.

        Args:
            task: The task to check

        Returns:
            bool: True if the task can be processed, False if it should wait
        """
        if not task.provider_id:
            return True  # Tasks with no provider can always be processed

        # Check if the provider is currently rate limited
        current_time = time.time()
        if self.provider_rate_limited[task.provider_id]:
            # Check if we've waited long enough
            if current_time < self.provider_backoff_until[task.provider_id]:
                return False  # Still in backoff period

            # Backoff period is over, clear the rate limit flag
            with self.state_lock:
                self.provider_rate_limited[task.provider_id] = False
                logger.info(
                    f"Provider '{task.provider_id}' backoff period ended, "
                    f"resuming processing"
                )

        return True

    def _handle_rate_limit(self, task: AudioGenerationTask) -> None:
        """
        Handle a rate limit error for a task.

        Updates the provider's rate limit state, calculates backoff time,
        and adds the task to the retry queue.

        Args:
            task: The task that hit a rate limit
        """
        if not task.provider_id:
            logger.warning(
                f"Task {task.idx} hit rate limit but has no provider_id, cannot apply provider-specific backoff"
            )
            return

        with self.state_lock:
            # Check if provider is already rate limited (concurrent in-flight task)
            was_already_rate_limited = self.provider_rate_limited[task.provider_id]

            # Mark the provider as rate limited and track when it happened
            self.provider_rate_limited[task.provider_id] = True
            current_time = time.time()
            self.provider_last_rate_limit_time[task.provider_id] = current_time

            # Only escalate backoff for the first task that hits rate limit
            # Concurrent in-flight tasks shouldn't escalate the backoff
            if not was_already_rate_limited:
                # Calculate backoff time (exponential backoff based on retry count)
                current_backoff = self.provider_backoff_time[task.provider_id]
                self.provider_backoff_until[task.provider_id] = (
                    current_time + current_backoff
                )

                # Increase backoff for next time
                self.provider_backoff_time[task.provider_id] = min(
                    current_backoff * self.backoff_factor, MAX_BACKOFF_SECONDS
                )

                logger.info(
                    f"Task {task.idx} hit rate limit for provider '{task.provider_id}' (first), "
                    f"retry {task.retry_count + 1}/{self.max_retries} scheduled in {current_backoff:.2f}s. "
                    f"Provider locked until backoff period ends."
                )
            else:
                # This is a concurrent in-flight task, don't escalate backoff
                logger.info(
                    f"Task {task.idx} hit rate limit for provider '{task.provider_id}' (concurrent), "
                    f"retry {task.retry_count + 1}/{self.max_retries} will use existing backoff period."
                )

            # Update task status and retry count
            task.status = TaskStatus.FAILED_RATE_LIMIT
            task.retry_count += 1

            # Add to retry queue if under max retries
            if task.retry_count <= self.max_retries:
                self.rate_limited_tasks[task.provider_id].append(task)
            else:
                logger.error(
                    f"Task {task.idx} exceeded max retries ({self.max_retries}), "
                    f"giving up after {task.retry_count} attempts"
                )
                task.status = TaskStatus.FAILED_OTHER  # Mark as permanent failure

    def _process_single_task(
        self, task: AudioGenerationTask
    ) -> Optional[ReportingState]:
        """
        Process a single audio generation task.

        Args:
            task: The task to process

        Returns:
            Optional[ReportingState]: Reporting state for the task if successful, None otherwise

        Raises:
            TTSRateLimitError: If the provider hits a rate limit (for retry handling)
            Exception: For other errors
        """
        task_reporting_state = ReportingState()

        # Update task status
        task.status = TaskStatus.PROCESSING

        # Print detailed information about the task
        logger.debug(f"\nProcessing dialogue #{task.idx} in thread")

        # Generate audio
        audio_data = None
        try:
            if task.expected_silence:
                logger.debug(f"  Task {task.idx}: Creating intentional silent audio.")
                silent_segment = AudioSegment.silent(duration=10)  # Short silent clip
                with io.BytesIO() as buf:
                    silent_segment.export(buf, format="mp3")
                    audio_data = buf.getvalue()
            else:
                logger.debug(f"  Task {task.idx}: Requesting audio generation...")
                audio_data = self.tts_provider_manager.generate_audio(
                    task.speaker, task.text_to_speak
                )

            if not audio_data:
                # Log error but let exception handling catch actual failures
                logger.error(
                    f"  TTS provider returned no audio data for task {task.idx}."
                )
                # Raise an exception to signal failure in the main loop
                raise ValueError(
                    f"TTS provider returned no audio data for task {task.idx}"
                )

            print_audio_task_details(task, logger, log_prefix="  ")
            logger.debug(
                f"  Audio generated successfully for task {task.idx} (size: {len(audio_data)} bytes)."
            )

            # Check for silence
            if self.silence_threshold is not None and not task.expected_silence:
                is_silent = check_audio_silence(
                    task=task,
                    audio_data=audio_data,
                    silence_threshold=self.silence_threshold,
                    reporting_state=task_reporting_state,
                    log_prefix=f"  Task {task.idx}: ",
                )
                if is_silent:
                    logger.warning(
                        f"  Task {task.idx}: Newly generated audio is silent."
                    )

            # Save to cache
            try:
                import os

                os.makedirs(os.path.dirname(task.cache_filepath), exist_ok=True)
                with open(task.cache_filepath, "wb") as f:
                    f.write(audio_data)
                task.is_cache_hit = True  # Mark as cached *after* successful save
                task.status = TaskStatus.GENERATED
                logger.debug(
                    f"  Task {task.idx}: Saved generated audio to {task.cache_filepath}"
                )
            except Exception as e:
                logger.error(
                    f"  Task {task.idx}: Error saving generated audio to cache: {e}"
                )
                raise  # Propagate save error

        except TTSRateLimitError as e:
            # Pass through rate limit errors for special handling in the main loop
            logger.warning(f"  Task {task.idx}: Hit rate limit: {e}")
            raise
        except Exception as e:
            # Mark any other error as a general failure
            task.status = TaskStatus.FAILED_OTHER
            logger.error(
                f"  Task {task.idx}: Error generating/processing audio: {e}",
                exc_info=False,
            )
            raise

        return task_reporting_state

    def _task_needs_processing(self, task: AudioGenerationTask) -> bool:
        """
        Determine if a task needs processing or can be skipped.

        Args:
            task: The task to check

        Returns:
            bool: True if the task needs processing, False if it can be skipped
        """
        # Skip if already cached
        if task.is_cache_hit:
            task.status = TaskStatus.CACHED
            return False

        # Skip if it's a duplicate that will be handled by another task
        if task.expected_cache_duplicate:
            task.status = TaskStatus.SKIPPED_DUPLICATE
            return False

        return True

    def _retry_rate_limited_tasks(self) -> List[AudioGenerationTask]:
        """
        Check for tasks that hit rate limits and can now be retried.

        Returns:
            List[AudioGenerationTask]: List of tasks that can be retried
        """
        current_time = time.time()
        tasks_to_retry = []

        with self.state_lock:
            # Check each provider with rate-limited tasks
            for provider_id, tasks in list(self.rate_limited_tasks.items()):
                # If backoff period is over, we can retry tasks for this provider
                if current_time >= self.provider_backoff_until[provider_id]:
                    self.provider_rate_limited[provider_id] = False

                    # Clear the rate limited tasks list and add them to retry list
                    tasks_to_retry.extend(tasks)
                    self.rate_limited_tasks[provider_id] = []
                    logger.info(
                        f"Provider '{provider_id}' backoff period ended, "
                        f"retrying {len(tasks)} tasks"
                    )

        return tasks_to_retry

    def run(self) -> ReportingState:
        """
        Run the audio download process with provider-specific concurrency limits,
        rate limit handling, backoff, and retry logic.

        Returns:
            ReportingState: The final reporting state
        """
        logger.info(
            f"Starting audio download manager with global limit of {self.global_max_workers} workers"
        )

        # Initialize task queues
        self.pending_tasks = [
            task for task in self.tasks if self._task_needs_processing(task)
        ]
        logger.info(f"Initial pending tasks: {len(self.pending_tasks)}")

        # Track skipped and cached tasks
        skipped_count = sum(
            1 for task in self.tasks if task.status == TaskStatus.SKIPPED_DUPLICATE
        )
        cached_count = sum(1 for task in self.tasks if task.status == TaskStatus.CACHED)
        logger.info(
            f"Skipped duplicates: {skipped_count}, Already cached: {cached_count}"
        )

        while self.pending_tasks or any(self.rate_limited_tasks.values()):
            # Check for rate-limited tasks that can be retried
            retry_tasks = self._retry_rate_limited_tasks()
            if retry_tasks:
                logger.info(
                    f"Adding {len(retry_tasks)} tasks back to pending queue for retry"
                )
                self.pending_tasks.extend(retry_tasks)

            # If no tasks are ready to process, wait a bit and check again
            if not self.pending_tasks:
                # Log current state for debugging
                rate_limited_count = sum(
                    len(tasks) for tasks in self.rate_limited_tasks.values()
                )
                if rate_limited_count > 0:
                    logger.debug(
                        f"Waiting for rate limit backoff to expire ({rate_limited_count} tasks waiting)"
                    )
                time.sleep(0.5)  # Short sleep to avoid CPU spinning
                continue

            # Process tasks with thread pool
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.global_max_workers
            ) as executor:
                # Submit tasks that are ready to process
                futures_map: Dict[concurrent.futures.Future, AudioGenerationTask] = {}

                # First pass: just identify tasks we can submit
                tasks_to_submit = []
                for task in self.pending_tasks:
                    if self._can_process_task(task):
                        tasks_to_submit.append(task)

                # Second pass: actually submit the tasks and acquire semaphores
                for task in tasks_to_submit:
                    # Create a wrapped task function that acquires and releases semaphores
                    def wrapped_task_fn(
                        task: AudioGenerationTask = task,
                    ) -> Optional[ReportingState]:
                        provider_id = task.provider_id
                        provider_semaphore = None

                        # Acquire provider semaphore if available
                        if provider_id and provider_id in self.provider_semaphores:
                            provider_semaphore = self.provider_semaphores[provider_id]
                            provider_semaphore.acquire()

                        # Always acquire global semaphore
                        self.global_semaphore.acquire()

                        try:
                            # Check rate limit status AFTER acquiring semaphores
                            # This prevents tasks from executing if rate limit was hit
                            # by another concurrent task after initial submission
                            if not self._can_process_task(task):
                                # Skipping logging due to potential log spam in high rate-limit situations
                                # logger.debug(
                                #    f"Task {task.idx} deferred due to provider '{provider_id}' rate limit"
                                # )
                                # Return None to indicate task should be retried later
                                # The task will be re-added to pending queue
                                return None

                            # Process the task
                            return self._process_single_task(task)
                        finally:
                            # Release semaphores
                            self.global_semaphore.release()
                            if provider_semaphore:
                                provider_semaphore.release()

                    # Submit the wrapped task
                    future = executor.submit(wrapped_task_fn)
                    futures_map[future] = task

                # Remove submitted tasks from pending queue
                self.pending_tasks = [
                    task for task in self.pending_tasks if task not in tasks_to_submit
                ]

                if not futures_map:
                    # If we couldn't submit any tasks, wait a bit before checking again
                    time.sleep(0.5)
                    continue

                # Log provider distribution of submitted tasks
                provider_counts: Dict[str, int] = {}
                for task in tasks_to_submit:
                    provider_id = task.provider_id or "unknown"
                    provider_counts[provider_id] = (
                        provider_counts.get(provider_id, 0) + 1
                    )

                provider_info = ", ".join(
                    [
                        f"{provider}: {count}"
                        for provider, count in provider_counts.items()
                    ]
                )
                logger.info(
                    f"Submitted {len(futures_map)} tasks to thread pool ({provider_info})"
                )

                # Process completed tasks with a progress bar
                with tqdm(
                    total=len(futures_map),
                    desc="Fetching Audio",
                    unit="clip",
                    file=sys.stderr,
                    leave=False,
                    mininterval=0.1,  # Update more frequently
                    dynamic_ncols=True,  # Adapt to terminal resizing
                ) as progress_bar:
                    for future in concurrent.futures.as_completed(futures_map):
                        task = futures_map[future]
                        try:
                            # Get the result (may raise an exception)
                            task_reporting_state = future.result()

                            # Check if task was deferred due to rate limit
                            if task_reporting_state is None:
                                # Task was skipped due to rate limit, add back to pending
                                with self.state_lock:
                                    self.pending_tasks.append(task)
                                # Skipping logging due to potential log spam in high rate-limit situations
                                # logger.debug(f"Task {task.idx} deferred due to provider '{task.provider_id}' rate limit")
                                # Don't update progress bar for deferred tasks
                                continue

                            # Update progress bar
                            progress_bar.update(1)

                            # If successful, merge reporting state
                            if task_reporting_state:
                                with self.state_lock:
                                    self.reporting_state.silent_clips.update(
                                        task_reporting_state.silent_clips
                                    )
                                    # Add other reporting fields if necessary in the future

                            # Mark as completed
                            with self.state_lock:
                                self.completed_tasks.append(task)

                                # Conservative backoff reset: only reset if we've had sustained success
                                # Reset backoff only if we've gone 2x the current backoff time without hitting rate limits
                                if (
                                    task.provider_id
                                    and task.provider_id in self.provider_backoff_time
                                ):
                                    current_time = time.time()
                                    current_backoff = self.provider_backoff_time[
                                        task.provider_id
                                    ]
                                    last_rate_limit_time = (
                                        self.provider_last_rate_limit_time[
                                            task.provider_id
                                        ]
                                    )

                                    # Calculate grace period (2x current backoff time)
                                    grace_period = current_backoff * 2
                                    time_since_last_rate_limit = (
                                        current_time - last_rate_limit_time
                                    )

                                    if (
                                        current_backoff > self.initial_backoff_seconds
                                        and time_since_last_rate_limit >= grace_period
                                    ):
                                        old_backoff = current_backoff
                                        self.provider_backoff_time[task.provider_id] = (
                                            self.initial_backoff_seconds
                                        )
                                        logger.info(
                                            f"Task {task.idx} completed successfully, "
                                            f"reset provider '{task.provider_id}' backoff from {old_backoff:.2f}s to {self.initial_backoff_seconds:.2f}s "
                                            f"after {time_since_last_rate_limit:.1f}s grace period"
                                        )
                                    elif current_backoff > self.initial_backoff_seconds:
                                        # Log when we're still in grace period
                                        remaining_grace = (
                                            grace_period - time_since_last_rate_limit
                                        )
                                        logger.debug(
                                            f"Task {task.idx} completed successfully, "
                                            f"provider '{task.provider_id}' backoff remains at {current_backoff:.2f}s "
                                            f"(grace period: {remaining_grace:.1f}s remaining)"
                                        )

                            logger.debug(f"Task {task.idx} completed successfully")

                        except TTSRateLimitError:
                            # Handle rate limit with exponential backoff
                            self._handle_rate_limit(task)
                            # Update progress bar even for failed tasks
                            progress_bar.update(1)

                        except Exception as e:
                            # Handle other errors
                            task.status = TaskStatus.FAILED_OTHER
                            logger.error(f"Task {task.idx} failed with error: {e}")
                            with self.state_lock:
                                self.completed_tasks.append(task)
                            # Update progress bar even for failed tasks
                            progress_bar.update(1)

        return self.reporting_state
