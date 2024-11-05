from functools import wraps
from typing import Callable, Any
from .logger import AgentLogger

logger = AgentLogger("ErrorHandler")

def handle_agent_errors(error_response: str = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                return error_response or f"An error occurred: {str(e)}"
        return wrapper
    return decorator 