from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from services.openai_service import OpenAIService
from .utils.logger import AgentLogger

class BaseRouter(ABC):
    def __init__(self, openai_service: OpenAIService):
        self.agent_interactions = set()
        self.openai_service = openai_service
        self.logger = AgentLogger("Router")
    
    @abstractmethod
    def classify_query(self, query: str) -> str:
        """Classify the query into a single category.
        
        Args:
            query: User's input query
            
        Returns:
            str: Classified category name
        """
        pass
    
    def _get_completion(self, messages: List[Dict[str, str]], model: str = "gpt-4-turbo-preview", max_tokens: int = 100) -> Optional[str]:
        """Get completion with error handling and logging.
        
        Args:
            messages: List of message dictionaries containing role and content
            model: OpenAI model identifier to use
            max_tokens: Maximum tokens in the response
            
        Returns:
            Optional[str]: Generated response or None if error occurs
            
        Raises:
            Exception: If OpenAI API call fails
        """
        try:
            return self.openai_service.get_completion(messages, model, max_tokens)
        except Exception as e:
            self.logger.logger.error(f"Completion error in router: {str(e)}")
            return None