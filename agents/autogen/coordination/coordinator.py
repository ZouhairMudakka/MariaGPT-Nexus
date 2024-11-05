from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from ..state_manager import AgentStateManager
from ...utils.logger import Logger

class AgentCoordinator:
    def __init__(self, 
                 state_manager: AgentStateManager,
                 logger: Logger):
        self.state_manager = state_manager
        self.logger = logger
        self.coordination_rules: Dict[str, Dict[str, Any]] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
        self.config = None
        self.performance_monitor = None
        
    async def coordinate_agents(self, 
                              task: Dict[str, Any],
                              available_agents: List[str]) -> Dict[str, Any]:
        """Coordinate agents for task execution."""
        try:
            # Determine optimal agent allocation
            assigned_agents = await self._allocate_agents(task, available_agents)
            
            # Create coordination plan
            plan = await self._create_coordination_plan(task, assigned_agents)
            
            # Update agent states
            for agent_id in assigned_agents:
                await self.state_manager.update_state(
                    agent_id,
                    {
                        "status": "assigned",
                        "context": {"task_id": task["id"]},
                        "metadata": {"coordination_plan": plan}
                    }
                )
            
            return {
                "task_id": task["id"],
                "assigned_agents": assigned_agents,
                "coordination_plan": plan,
                "status": "coordinated"
            }
            
        except Exception as e:
            self.logger.error(f"Coordination error: {str(e)}")
            raise
            
    async def _allocate_agents(self, 
                             task: Dict[str, Any],
                             available_agents: List[str]) -> List[str]:
        """Allocate optimal agents based on task requirements and agent capabilities."""
        try:
            task_type = task.get("type", "general")
            priority = task.get("priority", "medium")
            required_skills = task.get("required_skills", [])
            
            # Filter agents by required skills
            qualified_agents = [
                agent for agent in available_agents
                if self._agent_matches_requirements(agent, required_skills)
            ]
            
            if not qualified_agents:
                self.logger.warning(f"No qualified agents found for task: {task_type}")
                return available_agents[:2]
                
            # Sort agents by relevance score
            scored_agents = [
                (agent, self._calculate_agent_score(agent, task))
                for agent in qualified_agents
            ]
            scored_agents.sort(key=lambda x: x[1], reverse=True)
            
            # Select optimal number of agents based on task complexity
            num_agents = self._determine_optimal_team_size(task)
            return [agent for agent, _ in scored_agents[:num_agents]]
            
        except Exception as e:
            self.logger.error(f"Agent allocation error: {str(e)}")
            return available_agents[:2]
        
    def _agent_matches_requirements(self, agent: str, required_skills: List[str]) -> bool:
        """Check if agent matches required skills."""
        agent_skills = self.agent_capabilities.get(agent, [])
        return all(skill in agent_skills for skill in required_skills)
        
    def _calculate_agent_score(self, agent: str, task: Dict[str, Any]) -> float:
        """Calculate relevance score for agent-task pair."""
        base_score = 0.0
        agent_config = self.config.AGENT_CONFIGS.get(agent, {})
        
        # Add scoring logic based on agent specialization, past performance, etc.
        if task.get("type") in agent_config.get("specializations", []):
            base_score += 2.0
        
        # Add historical performance score
        performance_score = self.performance_monitor.get_agent_score(agent)
        return base_score + performance_score
        
    def _determine_optimal_team_size(self, task: Dict[str, Any]) -> int:
        """Determine optimal number of agents based on task complexity."""
        complexity = task.get("complexity", "medium")
        return {
            "low": 1,
            "medium": 2,
            "high": 3
        }.get(complexity, 2)
        
    async def _create_coordination_plan(self,
                                     task: Dict[str, Any],
                                     assigned_agents: List[str]) -> Dict[str, Any]:
        """Create detailed coordination plan."""
        return {
            "sequence": assigned_agents,
            "transitions": self._generate_transition_rules(assigned_agents),
            "fallback": assigned_agents[-1]
        }
        
    def _generate_transition_rules(self, agents: List[str]) -> Dict[str, Any]:
        """Generate rules for agent transitions."""
        rules = {}
        for i in range(len(agents) - 1):
            rules[f"{agents[i]}_to_{agents[i+1]}"] = {
                "condition": "task_requirement_met",
                "handoff_data": ["context", "state", "progress"]
            }
        return rules 