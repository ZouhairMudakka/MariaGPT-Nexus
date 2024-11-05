from typing import Dict, List, Optional, Any
from ...utils.logger import Logger

class PriorityManager:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.priority_levels = {
            "maria": 1,      # Primary contact
            "technical": 2,  # Technical specialist
            "sales": 2,     # Sales specialist
            "scheduler": 2   # Scheduling specialist
        }
        self.fallback_map = {
            "technical": ["maria"],
            "sales": ["maria"],
            "scheduler": ["maria"],
            "maria": []  # No fallback for primary agent
        }
        
    async def get_next_available_agent(self, 
                                     current_agent: str, 
                                     task_type: str,
                                     attempted_agents: List[str]) -> Optional[str]:
        """Get next available agent based on priority and fallback rules."""
        try:
            # Get fallback options
            fallback_options = self.fallback_map.get(current_agent, [])
            
            # Filter out already attempted agents
            available_options = [
                agent for agent in fallback_options 
                if agent not in attempted_agents
            ]
            
            if not available_options:
                return None
                
            # Sort by priority level
            return min(available_options, key=lambda x: self.priority_levels.get(x, 99))
            
        except Exception as e:
            self.logger.error(f"Error getting next available agent: {str(e)}")
            return None
            
    def get_agent_priority(self, agent_type: str) -> int:
        """Get priority level for an agent type."""
        return self.priority_levels.get(agent_type, 99) 