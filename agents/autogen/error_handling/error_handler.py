from typing import Dict, Optional, Tuple, Any
from datetime import datetime
from collections import defaultdict
from ...utils.logger import Logger
from ..config import AutoGenConfig

class AutoGenErrorHandler:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.last_errors: Dict[str, datetime] = {}
        
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        error_type = type(error).__name__
        self.error_counts[error_type] += 1
        self.last_errors[error_type] = datetime.now()
        
        if error_type in AutoGenConfig.DEFAULT_CONFIG["error_handling"]["retry_on_errors"]:
            return await self._handle_retryable_error(error, context)
        
        return await self._handle_non_retryable_error(error, context) 