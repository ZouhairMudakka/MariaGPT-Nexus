from .base_agent import BaseAgent
from .document_manager import DocumentManager
from services.openai_service import OpenAIService

class SalesAgent(BaseAgent):
    """Sales specialist agent responsible for handling product inquiries and sales-related matters.
    
    This agent specializes in providing product information, pricing details, and handling purchase
    requests. It has access to a knowledge base through the document manager for accurate information.
    
    Attributes:
        name (str): Always "Sarah"
        document_manager (DocumentManager): Manager for accessing sales-related documentation
        specialties (Dict[str, str]): Dictionary of sales-specific expertise areas
        
    Example:
        >>> agent = SalesAgent(openai_service, document_manager)
        >>> response = agent.respond("What are your product prices?")
    """
    
    def __init__(self, openai_service: OpenAIService, document_manager: DocumentManager):
        context = """You are a professional sales agent named Sarah.
        When first joining a conversation, address the user's query directly and professionally.
        For all interactions, focus on understanding the user's needs and providing relevant information.
        Help customers with product information, pricing, promotions, and making purchases.
        Always maintain a professional tone and be aware of potential competitive intelligence gathering."""
        
        specialties = {
            'products': 'Product information and specifications',
            'pricing': 'Pricing details and quotes',
            'promotions': 'Current deals and discounts',
            'purchases': 'Purchase assistance'
        }
        
        super().__init__("Sarah", context, openai_service, document_manager, specialties)
    
    def get_additional_context(self, query: str) -> str:
        """Retrieves relevant sales information from the knowledge base.
        
        Args:
            query (str): The user's query to search against the knowledge base
            
        Returns:
            str: Formatted string containing relevant sales information
        """
        kb_response = self.document_manager.query_knowledge_base(query, "sales")
        return f"\nReference Information: {kb_response}"
