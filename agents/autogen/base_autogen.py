from typing import Dict, List, Optional, Any, Tuple
import autogen
from .config import AutoGenConfig
from .workflows.conversation import ConversationWorkflow
from .workflows.task_management import TaskManager, EnhancedTaskManager
from .state_manager import AgentStateManager
from .monitoring.performance_monitor import PerformanceMonitor
from .coordination.coordinator import AgentCoordinator
from .coordination.priority_manager import PriorityManager
from datetime import datetime

class AutoGenManager:
    def __init__(self):
        self.config = AutoGenConfig()
        self.agents: Dict[str, autogen.AssistantAgent] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._initialize_agents()
        self.state_manager = AgentStateManager(self.logger)
        self.performance_monitor = PerformanceMonitor(self.logger, self.metrics_logger)
        self.coordinator = AgentCoordinator(self.state_manager, self.logger)
        self.priority_manager = PriorityManager(self.logger)

    def _initialize_agents(self):
        # Initialize Maria as the primary assistant
        self.agents["maria"] = autogen.AssistantAgent(
            name="Maria",
            system_message=self.config.AGENT_CONFIGS["maria"]["system_message"],
            llm_config=self.config.get_llm_config()
        )

        # Initialize specialized agents
        for agent_type in ["technical", "sales"]:
            config = self.config.get_agent_config(agent_type)
            self.agents[agent_type] = autogen.AssistantAgent(
                name=config["name"],
                system_message=config["system_message"],
                llm_config=self.config.get_llm_config()
            )

        # Initialize user proxy
        self.user_proxy = autogen.UserProxyAgent(
            name="User",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0
        )

    def create_group_chat(self, agents: Optional[List[str]] = None) -> autogen.GroupChat:
        if agents is None:
            agents = list(self.agents.keys())
        
        participants = [self.agents[agent] for agent in agents if agent in self.agents]
        participants.append(self.user_proxy)
        
        self.group_chat = autogen.GroupChat(
            agents=participants,
            messages=[],
            max_round=10
        )
        return self.group_chat

    def initiate_chat(self, message: str, agents: Optional[List[str]] = None):
        if not self.group_chat:
            self.create_group_chat(agents)

        self.user_proxy.initiate_chat(
            self.agents["maria"],
            message=message,
            group_chat=self.group_chat
        )

    async def create_session(self, session_id: str, agent_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new session with enhanced task management."""
        if session_id in self.sessions:
            return self.sessions[session_id]
            
        group_chat = self.create_group_chat(agent_types)
        session = {
            "id": session_id,
            "group_chat": group_chat,
            "conversation": ConversationWorkflow(group_chat),
            "task_manager": EnhancedTaskManager(group_chat, self.logger),
            "active_agents": agent_types or list(self.agents.keys()),
            "status": "active",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "error_count": 0
            }
        }
        
        self.sessions[session_id] = session
        return session

    async def process_message(self, session_id: str, message: str) -> Tuple[str, str]:
        """Process a message within a specific session."""
        try:
            if session_id not in self.sessions:
                await self.create_session(session_id)
                
            session = self.sessions[session_id]
            
            # Track performance
            start_time = datetime.now()
            
            # Process message
            response = await session["conversation"].process_message(message)
            
            # Monitor performance
            processing_time = (datetime.now() - start_time).total_seconds()
            await self.performance_monitor.track_metric(
                session_id,
                "response_time",
                processing_time,
                {"message_length": len(message)}
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            raise

    async def create_task(self, session_id: str, task_description: str, assigned_agents: List[str]) -> Optional[Dict[str, Any]]:
        """Create a task within a specific session."""
        if session_id not in self.sessions:
            return None
            
        session = self.sessions[session_id]
        return await session["task_manager"].create_task(task_description, assigned_agents)

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a session."""
        if session_id not in self.sessions:
            return None
            
        session = self.sessions[session_id]
        return {
            "id": session_id,
            "active_agents": session["active_agents"],
            "status": session["status"],
            "conversation_history": session["conversation"].conversation_history
        }