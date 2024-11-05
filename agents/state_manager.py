from typing import Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path

class ConversationState:
    def __init__(self):
        self.current_category: Optional[str] = None
        self.validated_contact_info: bool = False
        self.contact_info: Dict[str, Any] = {}
        self.meeting_details: Dict[str, Any] = {}
        self.last_agent: Optional[str] = None
        self.interaction_count: int = 0
        self.start_time: str = datetime.now().isoformat()
        self.agent_states: Dict[str, Dict[str, Any]] = {}
        
    def update_agent_state(self, agent_name: str, **kwargs):
        if agent_name not in self.agent_states:
            self.agent_states[agent_name] = {}
        self.agent_states[agent_name].update(kwargs)

class StateManager:
    def __init__(self, storage_dir: str = "data/conversation_states"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.conversation_states: Dict[str, ConversationState] = {}
    
    def get_state(self, conversation_id: str) -> ConversationState:
        if conversation_id not in self.conversation_states:
            self.conversation_states[conversation_id] = self._load_state(conversation_id)
        return self.conversation_states[conversation_id]
    
    def update_state(self, conversation_id: str, **kwargs):
        state = self.get_state(conversation_id)
        for key, value in kwargs.items():
            if key == 'contact_info' and value:
                state.validated_contact_info = True
                state.contact_info.update(value)
            else:
                setattr(state, key, value)
        self._save_state(conversation_id, state)
    
    def _load_state(self, conversation_id: str) -> ConversationState:
        state_file = self.storage_dir / f"{conversation_id}.json"
        if state_file.exists():
            with open(state_file) as f:
                data = json.load(f)
                state = ConversationState()
                for key, value in data.items():
                    setattr(state, key, value)
                return state
        return ConversationState()
    
    def _save_state(self, conversation_id: str, state: ConversationState):
        state_file = self.storage_dir / f"{conversation_id}.json"
        with open(state_file, 'w') as f:
            json.dump(state.__dict__, f, indent=2)