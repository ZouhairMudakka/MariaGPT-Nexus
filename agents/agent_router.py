from .base_router import BaseRouter
from .utils.logger import AgentLogger
from .customer_support_agent import CustomerSupportAgent
from .sales_agent import SalesAgent
from .scheduler_agent import SchedulerAgent
from .document_manager import DocumentManager
from services.openai_service import OpenAIService
from typing import Optional, List, Dict, Any

class AgentRouter(BaseRouter):
    """Routes user queries to appropriate specialized agents based on intent classification.
    
    This router maintains instances of all specialized agents and determines which agent
    should handle each query. It supports both single and multiple intent classification.
    
    Attributes:
        representative_agent: Front-desk representative agent that coordinates with specialists
        customer_support_agent (CustomerSupportAgent): Technical support specialist
        sales_agent (SalesAgent): Sales and product specialist
        scheduler_agent (SchedulerAgent): Meeting and calendar specialist
        
    Example:
        >>> router = AgentRouter(openai_service)
        >>> response = router.route_query("I need technical help")
    """

    def __init__(self, openai_service: OpenAIService):
        super().__init__(openai_service)
        self.representative_agent = None
        self.customer_support_agent = CustomerSupportAgent(openai_service)
        self.sales_agent = SalesAgent(openai_service, DocumentManager())
        self.scheduler_agent = SchedulerAgent(openai_service)
    
    def set_representative(self, agent) -> None:
        """Sets the representative agent for general queries.
        
        Args:
            agent: The RepresentativeAgent instance to handle general queries
        """
        self.representative_agent = agent
    
    def classify_query(self, query: str) -> str:
        try:
            messages = [{
                "role": "system",
                "content": """Classify the query into ONE of these categories:
                - technical_support: for technical system issues only
                - sales_inquiry: for new products and services only
                - scheduling: for appointments and meetings only
                - account_support: for account, billing, technical account issues
                - general: for HR, finance, or any other general inquiries that Maria handles directly
                
                Focus on the primary need. Return only the category name."""
            },
            {"role": "user", "content": query}]
            
            result = self._get_completion(messages).strip().lower()
            return result if result in ["technical_support", "sales_inquiry", "scheduling", "account_support", "general"] else "general"
        except Exception as e:
            self.logger.logger.error(f"Classification error: {str(e)}")
            return "general"

    def route_query(self, query: str) -> str:
        try:
            category = self.classify_query(query)
            conversation_context = self.representative_agent.conversation_history if self.representative_agent else []
            
            # Check if specialist was already introduced in this conversation
            specialist_already_introduced = any(
                msg.get('agent', '') != 'Maria' 
                for msg in conversation_context[-5:]  # Check last 5 messages
            )
            
            # Keep finance and general queries with Maria
            if category == "general":
                return "[Maria]: " + self._get_maria_response(query)
            
            # For specialist categories
            if category in ["account_support", "technical_support", "sales_inquiry", "scheduling"]:
                if not specialist_already_introduced:
                    introduction = self._get_maria_introduction(category)
                    specialist_response = self._get_agent_response(
                        category, 
                        query,
                        True,  # First interaction
                        conversation_context
                    )
                    return f"{introduction}\n{specialist_response}"
                else:
                    return self._get_agent_response(
                        category,
                        query,
                        False,  # Not first interaction
                        conversation_context
                    )
            
            return "[Maria]: I'll help you with that."
            
        except Exception as e:
            self.logger.logger.error(f"Query routing error: {str(e)}")
            return "[Maria]: I apologize, but I'm having trouble processing your request."

    def _get_maria_response(self, query: str) -> str:
        messages = [{
            "role": "system",
            "content": "You are Maria. Handle this query directly, focusing on HR, finance, and general assistance."
        },
        {"role": "user", "content": query}]
        
        response = self._get_completion(messages)
        return response if response else "How can I assist you with that?"

    def _get_agent_response(self, category: str, query: str, 
                       is_first_interaction: bool,
                       conversation_context: List[Dict[str, str]]) -> Optional[str]:
        """Get response from appropriate specialized agent.
        
        Args:
            category: Query category determining which agent to use
            query: User's input query
            is_first_interaction: Whether this is the first interaction with this agent
            conversation_context: Previous conversation messages for context
            
        Returns:
            Optional[str]: Agent's response or None if no appropriate agent found
        """
        if category == "technical_support":
            return self.customer_support_agent.respond(query, is_first_interaction, conversation_context)
        elif category == "sales_inquiry":
            return self.sales_agent.respond(query, is_first_interaction, conversation_context)
        elif category == "scheduling":
            return self.scheduler_agent.respond(query, is_first_interaction, conversation_context)
        elif category == "general" and self.representative_agent:
            return self.representative_agent.respond(query, is_first_interaction, conversation_context)
        return None

    def classify_multiple_intents(self, query: str) -> List[str]:
        """Analyze query for multiple possible intent categories.
        
        Args:
            query: User's input query
            
        Returns:
            List[str]: List of relevant categories
        """
        try:
            messages = [{
                "role": "system",
                "content": """Analyze the query and return ALL relevant categories as a comma-separated list:
                - technical_support: technical issues, account problems, IT support, system access
                - sales_inquiry: product info, pricing, purchases, finance, billing, payments, quotes
                - scheduling: appointments, meetings, calendar, availability, booking
                - general: HR inquiries, partnerships, press, marketing, media, careers, development, 
                          general questions, greetings, or any other category not listed above
                Example: "sales_inquiry, scheduling" for "I want to schedule a product demo" """
            },
            {"role": "user", "content": query}]
            
            result = self._get_completion(messages)
            return [cat.strip() for cat in result.split(',')] if result else ["general"]
        except Exception as e:
            self.logger.logger.error(f"Multiple intent classification error: {str(e)}", exc_info=True)
            return ["general"]

    def _analyze_response_for_followups(self, response: str, 
                                      original_categories: List[str],
                                      handled_categories: set) -> List[str]:
        """Analyze agent response to determine if other specialists should be involved."""
        try:
            messages = [{
                "role": "system",
                "content": """Analyze this response and determine if other specialists should be involved.
                Consider:
                1. Explicit mentions of needing other specialists
                2. Implicit needs based on the response content
                3. Related services or support that could benefit the user
                
                Return relevant categories as comma-separated list:
                - technical_support: for technical or system issues
                - sales_inquiry: for product pricing only
                - scheduling: for appointments only
                - general: keep with Maria for HR, finance, or general matters
                
                Return empty string if no additional specialists needed."""
            },
            {"role": "user", "content": response}]
            
            result = self._get_completion(messages)
            if not result:
                return []
                
            follow_ups = [cat.strip() for cat in result.split(',')]
            return [cat for cat in follow_ups 
                    if cat in original_categories 
                    and cat not in handled_categories
                    and cat != "general"]  # Prevent routing general queries away from Maria
        except Exception as e:
            self.logger.logger.error(f"Follow-up analysis error: {str(e)}")
            return []

    def _get_wrap_up_response(self, conversation_context: List[Dict[str, str]]) -> Optional[str]:
        """Generate a wrap-up response from Maria if needed."""
        try:
            messages = [{
                "role": "system",
                "content": """Review the conversation and determine if a wrap-up response is needed.
                Consider:
                1. Were all aspects of the user's inquiry addressed?
                2. Did specialists collaborate effectively?
                3. Are there any loose ends or potential needs not yet addressed?
                4. Would additional specialist involvement be beneficial?
                
                If yes, provide a brief response that:
                1. Acknowledges the collaboration of involved specialists
                2. Ensures all user needs were addressed
                3. Summarizes next steps or recommendations
                4. Offers to involve additional specialists if needed
                
                Return empty string if no wrap-up needed."""
            },
            {"role": "user", "content": str(conversation_context)}]
            
            return self._get_completion(messages)
        except Exception as e:
            self.logger.logger.error(f"Wrap-up generation error: {str(e)}")
            return None

    def _get_maria_introduction(self, category: str) -> str:
        specialist_map = {
            "account_support": "Alex, our account specialist",
            "technical_support": "Alex, our technical support specialist",
            "sales_inquiry": "Sarah, our sales specialist",
            "scheduling": "Mike, our scheduling specialist"
        }
        
        return f"[Maria]: Let me connect you with {specialist_map.get(category)}, who can better assist you with this."
