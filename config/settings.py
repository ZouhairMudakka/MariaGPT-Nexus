from typing import Dict, Any
import os
import json

class Settings:
    """Global settings management for the agent system."""
    
    def __init__(self):
        self.base_path = os.getenv('AGENT_BASE_PATH', 'data')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o')
        self.openai_mini_model = os.getenv('OPENAI_MINI_MODEL', 'gpt-4o-mini')
        self.max_history = int(os.getenv('MAX_HISTORY', '15'))
        self.max_tokens = int(os.getenv('MAX_TOKENS', '300'))
        self.email_settings = {
            'sender': os.getenv('EMAIL_SENDER', 'maria.gpt@mudakka.com'),
            'reply_to': os.getenv('EMAIL_REPLY_TO', 'noreply@mudakka.com')
        }
        self.google_settings = {
            'credentials_file': 'multiagent_demo_credentials.json',
            'token_file': 'token.pickle',
            'resources_folder': os.getenv('GOOGLE_RESOURCES_FOLDER'),
            'calendar_id': os.getenv('GOOGLE_CALENDAR_ID'),
            'knowledge_base_folder_id': os.getenv('GOOGLE_KNOWLEDGE_BASE_FOLDER_ID', '')
        }
        
    @property
    def paths(self) -> Dict[str, str]:
        existing_paths = {
            'conversations': f"{self.base_path}/conversations",
            'email_logs': f"{self.base_path}/email_logs",
            'user_interactions': f"{self.base_path}/user_interactions",
            'knowledge_base': f"{self.base_path}/knowledge_base"
        }
        # Add Google paths
        existing_paths['google_resources'] = f"{self.base_path}/google_resources"
        return existing_paths

settings = Settings() 