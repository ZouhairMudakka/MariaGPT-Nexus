from typing import Dict, Any
import os
from dotenv import load_dotenv


load_dotenv()

class AutoGenConfig:
    DEFAULT_CONFIG = {
        "temperature": 0.7,
        "max_tokens": 1000,
        "model": "gpt-4",
        "timeout": 600,
        "retry_attempts": 3,
        "retry_delay": 1,
        "max_concurrent_tasks": 5,
        "task_timeout": 300,
        "priority_levels": {
            "high": 3,
            "medium": 2,
            "low": 1
        },
        "group_chat": {
            "max_rounds": 10,
            "max_consecutive_auto_reply": 4,
            "allow_multi_agent_conversation": True,
            "agent_response_timeout": 30
        },
        "conversation": {
            "max_history_tokens": 2000,
            "summarize_after_messages": 20,
            "context_window": 10
        },
        "error_handling": {
            "max_retries": 3,
            "backoff_factor": 2,
            "retry_on_errors": ["TimeoutError", "APIError", "ConnectionError"]
        }
    }

    AGENT_CONFIGS = {
        "maria": {
            "name": "Maria",
            "system_message": """You are Maria, a friendly front-desk representative.
            You coordinate with specialized AI agents for technical support, sales, and scheduling matters.
            You handle HR, finance, and general inquiries directly.""",
            "human_input_mode": "NEVER",
            "max_consecutive_auto_reply": 4
        },
        "technical": {
            "name": "Alex",
            "system_message": "You are Alex, a technical support specialist...",
            "human_input_mode": "NEVER",
            "max_consecutive_auto_reply": 4
        },
        "sales": {
            "name": "Sarah",
            "system_message": "You are Sarah, a sales representative...",
            "human_input_mode": "NEVER",
            "max_consecutive_auto_reply": 4
        }
    }

    REQUIRED_FIELDS = {
        "agent": ["name", "system_message", "human_input_mode", "max_consecutive_auto_reply"],
        "llm": ["model", "api_key"],
        "task": ["max_retries", "timeout", "priority_levels"]
    }

    @classmethod
    def validate_config(cls, config_type: str, config: Dict[str, Any]) -> bool:
        """Validate configuration completeness."""
        required = cls.REQUIRED_FIELDS.get(config_type, [])
        return all(field in config for field in required)

    @classmethod
    def get_agent_config(cls, agent_type: str) -> Dict[str, Any]:
        """Get agent configuration with validation."""
        try:
            base_config = cls.DEFAULT_CONFIG.copy()
            agent_config = cls.AGENT_CONFIGS.get(agent_type)
            
            if not agent_config:
                raise ValueError(f"Unknown agent type: {agent_type}")
                
            base_config.update(agent_config)
            
            if not cls.validate_config("agent", base_config):
                raise ValueError(f"Invalid configuration for agent: {agent_type}")
                
            return base_config
            
        except Exception as e:
            logger.error(f"Error getting agent config: {str(e)}")
            raise ConfigurationError(f"Failed to get configuration for {agent_type}: {str(e)}")

    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """Get LLM configuration with API settings."""
        return {
            "config_list": [{
                "model": cls.DEFAULT_CONFIG["model"],
                "api_key": os.getenv("OPENAI_API_KEY"),
                "temperature": cls.DEFAULT_CONFIG["temperature"],
                "max_tokens": cls.DEFAULT_CONFIG["max_tokens"]
            }],
            "timeout": cls.DEFAULT_CONFIG["timeout"]
        }

    @classmethod
    def get_task_config(cls) -> Dict[str, Any]:
        """Get task-specific configuration."""
        return {
            "max_retries": cls.DEFAULT_CONFIG["retry_attempts"],
            "retry_delay": cls.DEFAULT_CONFIG["retry_delay"],
            "max_concurrent": cls.DEFAULT_CONFIG["max_concurrent_tasks"],
            "timeout": cls.DEFAULT_CONFIG["task_timeout"],
            "priority_levels": cls.DEFAULT_CONFIG["priority_levels"]
        }