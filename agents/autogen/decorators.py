from functools import wraps
from typing import Any, Callable
import logging

def handle_agent_errors(error_message: str):
    """Decorator to handle agent errors with custom error message."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Error in {func.__name__}: {str(e)}")
                return {"error": error_message}
        return wrapper
    return decorator 