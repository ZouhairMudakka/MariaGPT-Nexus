from typing import List, Dict, Any, Optional
import openai
from agents.utils.logger import AgentLogger

class OpenAIService:
    """Service for handling OpenAI API interactions with proper error handling and logging.
    
    This service manages all OpenAI API calls, including retries, rate limiting,
    and error handling. It provides a consistent interface for all agents.
    
    Attributes:
        logger (AgentLogger): Logger instance for tracking API interactions
        max_retries (int): Maximum number of retry attempts for failed calls
    """
    
    def __init__(self, api_key: str, max_retries: int = 3):
        self.logger = AgentLogger("OpenAIService")
        self.max_retries = max_retries
        openai.api_key = api_key
        # Configure logging levels
        import logging
        logging.getLogger("httpx").setLevel(logging.WARNING)

    def get_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "gpt-4o",
        max_tokens: int = 1500,
        temperature: float = 0.7
    ) -> Optional[str]:
        """Get completion from OpenAI API with error handling and retries.
        
        Args:
            messages: List of message dictionaries with role and content
            model: OpenAI model identifier
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0-1)
            
        Returns:
            Optional[str]: Generated response or None if all retries fail
            
        Raises:
            openai.APIError: If an unrecoverable API error occurs
        """
        attempt = 0
        while attempt < self.max_retries:
            try:
                response = openai.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return response.choices[0].message.content.strip()
                
            except openai.RateLimitError as e:
                self.logger.logger.warning(f"Rate limit hit, attempt {attempt + 1}/{self.max_retries}")
                attempt += 1
                if attempt == self.max_retries:
                    self.logger.logger.error("Rate limit retries exhausted")
                    raise
                    
            except openai.APIError as e:
                self.logger.logger.error(f"OpenAI API error: {str(e)}")
                raise
                
            except Exception as e:
                self.logger.logger.error(f"Unexpected error in OpenAI service: {str(e)}")
                raise

        return None