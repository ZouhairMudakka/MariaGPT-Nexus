from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
from .config import AutoGenConfig
from ..utils.logger import Logger

class EnhancedStateManager:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.states: Dict[str, Dict[str, Any]] = {}
        self.state_history: Dict[str, List[Dict[str, Any]]] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self.config = AutoGenConfig()
        
    async def update_state(self, agent_id: str, state_update: Dict[str, Any]) -> None:
        if agent_id not in self.locks:
            self.locks[agent_id] = asyncio.Lock()
            
        async with self.locks[agent_id]:
            await self._process_state_update(agent_id, state_update)
            
    async def _process_state_update(self, agent_id: str, state_update: Dict[str, Any]) -> None:
        try:
            current_state = self.states.get(agent_id, {})
            
            # Validate state update
            if not self._validate_state_update(state_update):
                raise ValueError("Invalid state update format")
                
            # Track state history
            await self._track_state_history(agent_id, current_state, state_update)
            
            # Update current state
            current_state.update(state_update)
            self.states[agent_id] = current_state
            
        except Exception as e:
            self.logger.error(f"State update error for agent {agent_id}: {str(e)}")
            raise
        
    def get_state(self, agent_id: str) -> Dict[str, Any]:
        """Get current agent state."""
        return self.states.get(agent_id, {})
        
    def get_state_history(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get agent state history."""
        return self.state_history.get(agent_id, [])
        
    def _validate_state_update(self, state_update: Dict[str, Any]) -> bool:
        """Validate state update format and content."""
        required_fields = {"status", "context", "metadata"}
        return all(field in state_update for field in required_fields) 