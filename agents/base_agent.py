from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import openai
import json
import os
from .utils.logger import AgentLogger
from services.openai_service import OpenAIService

class BaseAgent(ABC):
    """Base class for all AI agents in the system.
    
    Attributes:
        name (str): Agent's display name
        conversation_history (List[Dict]): History of all interactions
        introduced (bool): Whether agent has been introduced in conversation
        context (str): Agent's behavioral context and instructions
        specialties (Dict[str, str]): Agent's areas of expertise
        department_emails (Dict[str, str]): Department email mappings
        document_manager (Optional[Any]): Knowledge base document manager
    """
    
    def __init__(self, 
                 name: str, 
                 context: str,
                 openai_service: OpenAIService,
                 document_manager: Optional[Any] = None,
                 specialties: Optional[Dict[str, str]] = None, 
                 department_emails: Optional[Dict[str, str]] = None):
        self.name = name
        self.conversation_history: List[Dict[str, str]] = []
        self.introduced = False
        self.context = context
        self.specialties = specialties or {}
        self.department_emails = department_emails or {}
        self.document_manager = document_manager
        self.email_logs: List[Dict[str, str]] = []
        self.logger = AgentLogger(name)
        self.openai_service = openai_service
        
    def respond(self, 
                query: str, 
                is_first_interaction: bool = False, 
                conversation_context: Optional[List[Dict[str, str]]] = None) -> str:
        """Generate a response to the user's query.
        
        Args:
            query: The user's input text
            is_first_interaction: Whether this is the first interaction with this agent
            conversation_context: Previous conversation messages for context
            
        Returns:
            Formatted response string with agent name prefix
        """
        try:
            # Build messages including conversation history
            messages = [{"role": "system", "content": self.context}]
            
            # Add conversation context if available
            if conversation_context:
                for msg in conversation_context:
                    if msg.get('role') in ['user', 'assistant']:
                        messages.append({
                            "role": msg['role'],
                            "content": msg['content'].split(']:', 1)[-1].strip() if ']:' in msg['content'] else msg['content']
                        })
            
            # Add current query
            messages.append({"role": "user", "content": query})
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=800
            )
            
            response_content = response.choices[0].message.content.strip()
            
            # Handle introduction logic
            if is_first_interaction and not self.introduced:
                self.introduced = True
                was_introduced = any(
                    msg.get('name') == 'Maria' and 
                    'connect you with' in msg.get('content', '') 
                    for msg in (conversation_context or [])
                )
                if self.name != "Maria" and was_introduced and not response_content.startswith("Thank you, Maria"):
                    response_content = f"Thank you, Maria. {response_content}"
            
            return f"[{self.name}]: {response_content}"
            
        except Exception as e:
            error_msg = f"{self.name.lower()} error: {str(e)}"
            self.logger.logger.error(error_msg)
            return f"[{self.name}]: I apologize, but I'm having trouble processing your request. Please try again."
    
    def get_additional_context(self, query):
        """Override this method to add agent-specific context"""
        return ""
    
    def get_conversation_history(self):
        return self.conversation_history
    def validate_contact_info(self, text):
        """Common contact info validation method"""
        try:
            messages = [{
                "role": "system",
                "content": """Extract email and phone number from the text.
                Return as JSON: {"email": "extracted email or null", "phone": "extracted phone or null"}"""
            },
            {"role": "user", "content": text}]
            
            response = self.openai_service.get_completion(messages)
            return json.loads(response)
        except Exception as e:
            self.logger.logger.error(f"Contact validation error: {str(e)}")
            return {"email": None, "phone": None}

    def validate_meeting_details(self, query: str, available_slots: List[Dict] = None) -> Dict[str, Any]:
        """Extract and validate meeting details from query."""
        try:
            if available_slots:
                slot_info = "\n".join([
                    f"Slot {i+1}: {slot['start']}" 
                    for i, slot in enumerate(available_slots)
                ])
                
                messages = [{
                    "role": "system",
                    "content": f"""Extract meeting details from the text.
                    Available slots:\n{slot_info}\n
                    Return as JSON: {{
                        "is_complete": boolean,
                        "slot_number": "matched slot number or null",
                        "purpose": "meeting purpose or null"
                    }}"""
                },
                {"role": "user", "content": query}]
            else:
                messages = [{
                    "role": "system",
                    "content": """Extract meeting details from the text.
                    Return as JSON: {
                        "is_complete": boolean,
                        "date": "extracted date or null",
                        "time": "extracted time or null",
                        "duration": "extracted duration or null",
                        "purpose": "meeting purpose or null"
                    }"""
                },
                {"role": "user", "content": query}]
            
            response = self.openai_service.get_completion(messages)
            return json.loads(response)
        except Exception as e:
            self.logger.logger.error(f"Meeting validation error: {str(e)}")
            return {
                "is_complete": False,
                "slot_number": None,
                "purpose": None
            }

    def is_conversation_end(self, query):
        try:
            messages = [{
                "role": "system",
                "content": "Determine if this message indicates the end of a conversation. Return only 'true' or 'false'."
            },
            {"role": "user", "content": query}]
            
            response = self.openai_service.get_completion(messages, max_tokens=50)
            return response.lower() == "true"
        except Exception as e:
            self.logger.logger.error(f"Conversation end check error: {str(e)}")
            return False
