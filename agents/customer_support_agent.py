from .base_agent import BaseAgent
from services.openai_service import OpenAIService

class CustomerSupportAgent(BaseAgent):
    def __init__(self, openai_service: OpenAIService):
        context = """You are a helpful customer support agent named Alex.
        When first joining a conversation:
        1. Thank Maria for the introduction
        2. Briefly introduce yourself in a friendly, professional way
        3. Then address the user's query
        For subsequent interactions, respond directly to queries.
        Provide clear, concise, and friendly responses to customer queries."""
        
        specialties = {
            'account': 'Specialist in account-related issues',
            'technical': 'Technical support specialist',
            'billing': 'Billing and pricing expert'
        }
        
        super().__init__("Alex", context, openai_service, specialties=specialties)
