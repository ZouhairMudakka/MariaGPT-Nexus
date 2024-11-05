from typing import Dict, Any, Optional, List
import autogen
from .config import AutoGenConfig
from ..base_agent import BaseAgent

class AutoGenAgentFactory:
    def __init__(self):
        self.config = AutoGenConfig()
        self.agents: Dict[str, autogen.AssistantAgent] = {}
        
    def create_agent(self, agent_type: str, **kwargs) -> autogen.AssistantAgent:
        """Create an AutoGen agent with the specified configuration."""
        config = self.config.get_agent_config(agent_type)
        config.update(kwargs)
        
        agent = autogen.AssistantAgent(
            name=config["name"],
            system_message=config["system_message"],
            llm_config=self.config.get_llm_config()
        )
        
        self.agents[agent_type] = agent
        return agent
        
    def create_group(self, agent_types: List[str]) -> List[autogen.AssistantAgent]:
        """Create a group of agents for specified types."""
        return [
            self.create_agent(agent_type) 
            for agent_type in agent_types 
            if agent_type not in self.agents
        ]
        
    def get_or_create_agent(self, agent_type: str) -> autogen.AssistantAgent:
        """Get existing agent or create new one if not exists."""
        if agent_type not in self.agents:
            return self.create_agent(agent_type)
        return self.agents[agent_type]