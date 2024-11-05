from typing import Dict, Any, Optional
import json
import os
from datetime import datetime
from .logger import AgentLogger
from ..document_manager import DocumentManager

class FileManager:
    """Handles all file operations for the agent system."""
    
    def __init__(self, base_path: str = "data"):
        self.base_path = base_path
        self.logger = AgentLogger("FileManager")
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            'conversations',
            'email_logs',
            'user_interactions',
            'knowledge_base'
        ]
        for directory in directories:
            os.makedirs(os.path.join(self.base_path, directory), exist_ok=True)
    
    def save_conversation(self, 
                         conversation_id: str, 
                         data: Dict[str, Any]) -> bool:
        """Save conversation data to file."""
        try:
            file_path = os.path.join(
                self.base_path, 
                'conversations', 
                f"{conversation_id}.json"
            )
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Error saving conversation: {str(e)}")
            return False 