from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import asyncio
from ...utils.logger import Logger

class RecoveryStrategy:
    def __init__(self, logger: Logger):
        self.logger = logger
        
    async def retry_with_format_correction(self, context: Dict[str, Any]) -> bool:
        """Retry operation with corrected format."""
        try:
            messages = context.get("messages", [])
            if not messages:
                return False
                
            # Add format correction prompt
            messages.insert(0, {
                "role": "system",
                "content": """Ensure all responses follow these rules:
                1. Use valid JSON format
                2. No markdown formatting
                3. Keep responses concise and structured"""
            })
            
            response = await self.openai_service.get_completion(
                messages,
                temperature=0.3,
                max_tokens=150
            )
            
            # Validate JSON
            json.loads(response)
            return True
            
        except Exception as e:
            self.logger.error(f"Format correction failed: {str(e)}")
            return False
            
    async def restore_conversation_state(self, 
                                      recovery_states: Dict[int, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Restore to last valid conversation state."""
        try:
            if not recovery_states:
                return None
                
            # Get most recent valid state
            last_state_key = max(recovery_states.keys())
            return recovery_states[last_state_key]
            
        except Exception as e:
            self.logger.error(f"State restoration failed: {str(e)}")
            return None
            
    async def handle_timeout(self, context: Dict[str, Any], max_retries: int = 3) -> bool:
        """Handle timeout errors with exponential backoff."""
        try:
            delay = 1
            for attempt in range(max_retries):
                try:
                    await asyncio.sleep(delay)
                    # Attempt operation with increased timeout
                    async with asyncio.timeout(delay * 2):
                        await self._process_message(context)
                    return True
                except asyncio.TimeoutError:
                    delay *= 2
                    continue
            return False
            
        except Exception as e:
            self.logger.error(f"Timeout handling failed: {str(e)}")
            return False 