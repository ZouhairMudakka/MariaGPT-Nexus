from typing import Dict, List, Optional, Any, Tuple
import asyncio
from datetime import datetime, timedelta
from ..coordination.priority_manager import PriorityManager
from ..config import AutoGenConfig, ConfigurationError
from dataclasses import dataclass

@dataclass
class TaskDependency:
    task_id: int
    dependency_type: str  # 'blocking' or 'non-blocking'
    condition: str

class RetryableTask:
    def __init__(self, task: Dict[str, Any], config: Dict[str, Any]):
        self.task = task
        self.max_retries = config["max_retries"]
        self.retry_delay = config["retry_delay"]
        self.attempts = 0
        self.last_error = None
        
    async def execute(self, func) -> Tuple[bool, Optional[Any]]:
        """Execute task with retry logic."""
        while self.attempts < self.max_retries:
            try:
                result = await func(self.task)
                return True, result
            except Exception as e:
                self.attempts += 1
                self.last_error = str(e)
                
                if self.attempts < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** (self.attempts - 1)))
                    continue
                    
                return False, None
                
        return False, None

class EnhancedTaskManager:
    def __init__(self, group_chat: autogen.GroupChat, logger: Logger):
        self.group_chat = group_chat
        self.logger = logger
        self.config = AutoGenConfig()
        self.task_config = self.config.get_task_config()
        self.tasks: List[Dict[str, Any]] = []
        self.retryable_tasks: Dict[int, RetryableTask] = {}
        
    async def create_task(self, 
                         task_description: str, 
                         assigned_agents: List[str],
                         priority: int = 1,
                         dependencies: List[TaskDependency] = None) -> Dict[str, Any]:
        """Create a new task with priority and dependencies."""
        task_id = len(self.tasks)
        
        task = {
            "id": task_id,
            "description": task_description,
            "assigned_agents": assigned_agents,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "metadata": {
                "attempts": 0,
                "last_attempt": None,
                "error_count": 0
            }
        }
        
        if dependencies:
            self.dependencies[task_id] = dependencies
            
        self.tasks.append(task)
        await self._update_task_queue()
        return task
        
    async def _update_task_queue(self) -> None:
        """Update task queue based on priorities and dependencies."""
        try:
            # Sort tasks by priority and dependencies
            pending_tasks = [
                task for task in self.tasks 
                if task["status"] == "pending"
            ]
            
            sorted_tasks = sorted(
                pending_tasks,
                key=lambda x: (
                    -x["priority"],  # Higher priority first
                    x["metadata"]["attempts"],  # Fewer attempts first
                    x["created_at"]  # Older tasks first
                )
            )
            
            # Update task order
            self.tasks = [
                task for task in self.tasks 
                if task["status"] != "pending"
            ] + sorted_tasks
            
        except Exception as e:
            self.logger.error(f"Error updating task queue: {str(e)}")

    async def process_task(self, task_id: int) -> Optional[str]:
        """Process a task with retry logic."""
        if task_id not in self.retryable_tasks:
            task = self.tasks[task_id]
            self.retryable_tasks[task_id] = RetryableTask(task, self.task_config)
            
        retryable = self.retryable_tasks[task_id]
        success, result = await retryable.execute(self._execute_task)
        
        if success:
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["result"] = result
            return result
        else:
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["error"] = retryable.last_error
            return None
            
    async def _execute_task(self, task: Dict[str, Any]) -> str:
        """Execute a single task."""
        return await task["group_chat"].process_message(
            message=task["description"],
            sender=task["group_chat"].agents[0]
        )
