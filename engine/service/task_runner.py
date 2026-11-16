"""
Background Task Runner and Job Manager for Premiere AI Editor Local Engine.

Provides:
- Thread-pool background execution of CPU/GPU intensive tasks (transcription, silence detection)
- Asynchronous progress reporting (0-100%, stage description)
- Clean task cancellation
- Thread-safe result caching and retrieval
"""

import time
import uuid
import threading
from typing import Dict, Any, Callable, Optional


class Task:
    """Represents an asynchronous background job."""

    def __init__(self, task_id: str, task_type: str):
        self.task_id = task_id
        self.task_type = task_type
        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.progress = 0.0
        self.stage = "Queued"
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = time.time()
        self.completed_at: Optional[float] = None
        self.cancel_requested = False

    def update_progress(self, percent: float, stage: str):
        self.progress = round(max(0.0, min(100.0, float(percent))), 1)
        self.stage = stage

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "has_result": self.result is not None,
            "error": self.error,
        }


class TaskRunner:
    """Manages active and completed background tasks."""

    def __init__(self, max_history: int = 50):
        self.tasks: Dict[str, Task] = {}
        self.max_history = max_history
        self._lock = threading.Lock()

    def create_task(self, task_type: str) -> Task:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = Task(task_id, task_type)
        with self._lock:
            self.tasks[task_id] = task
            # Cleanup old tasks if exceeded history
            if len(self.tasks) > self.max_history:
                oldest = sorted(self.tasks.values(), key=lambda t: t.created_at)[0]
                del self.tasks[oldest.task_id]
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self.tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status in ("pending", "running"):
                task.cancel_requested = True
                task.status = "cancelled"
                task.stage = "Cancelled by user"
                return True
        return False

    def run_async(
        self,
        task: Task,
        worker_fn: Callable[[Task, Callable[[float, str], None]], Dict[str, Any]],
    ) -> None:
        """Launches worker function in a background daemon thread."""
        def _thread_target():
            task.status = "running"
            task.stage = "Starting..."

            def _progress(pct: float, stage_msg: str):
                task.update_progress(pct, stage_msg)

            try:
                result = worker_fn(task, _progress)
                if not task.cancel_requested:
                    task.result = result
                    task.status = "completed"
                    task.progress = 100.0
                    task.stage = "Completed successfully."
                    task.completed_at = time.time()
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                task.stage = f"Error: {e}"
                task.completed_at = time.time()

        t = threading.Thread(target=_thread_target, daemon=True)
        t.start()
