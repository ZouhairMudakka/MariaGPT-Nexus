import pytest
from agents.agent_router import AgentRouter

def test_agent_router_initialization(mock_openai_service):
    router = AgentRouter(mock_openai_service)
    assert router.representative_agent is None
    assert router.customer_support_agent is not None
    assert router.sales_agent is not None
    assert router.scheduler_agent is not None

def test_classify_query(mock_openai_service):
    router = AgentRouter(mock_openai_service)
    mock_openai_service.get_completion.return_value = "technical_support"
    result = router.classify_query("I have a problem with my account")
    assert result == "technical_support"

def test_classify_multiple_intents(mock_openai_service):
    router = AgentRouter(mock_openai_service)
    mock_openai_service.get_completion.return_value = "sales_inquiry, scheduling"
    result = router.classify_multiple_intents("I want to schedule a demo of your product")
    assert "sales_inquiry" in result
    assert "scheduling" in result

def test_route_query_with_multiple_agents(mock_openai_service):
    router = AgentRouter(mock_openai_service)
    mock_openai_service.get_completion.return_value = "sales_inquiry"
    response = router.route_query("Tell me about your pricing")
    assert response is not None 

def test_get_agent_response(mock_openai_service):
    router = AgentRouter(mock_openai_service)
    
    # Test technical support routing
    response = router._get_agent_response("technical_support", "test query", True, None)
    assert response is not None
    
    # Test sales routing
    response = router._get_agent_response("sales_inquiry", "test query", True, None)
    assert response is not None
    
    # Test scheduling routing
    response = router._get_agent_response("scheduling", "test query", True, None)
    assert response is not None
    
    # Test general routing without representative
    response = router._get_agent_response("general", "test query", True, None)
    assert response is None

def test_route_query_with_conversation_context(mock_openai_service):
    router = AgentRouter(mock_openai_service)
    conversation_context = [
        {"name": "User", "content": "Previous message"},
        {"name": "Maria", "content": "Previous response"}
    ]
    
    mock_openai_service.get_completion.return_value = "technical_support"
    response = router.route_query("test query", conversation_context=conversation_context)
    assert response is not None

def test_classify_multiple_intents(mock_openai_service):
    router = AgentRouter(mock_openai_service)
    mock_openai_service.get_completion.return_value = "sales_inquiry, scheduling"
    
    result = router.classify_multiple_intents("I want to schedule a product demo")
    assert len(result) == 2
    assert "sales_inquiry" in result
    assert "scheduling" in result
    
    # Test error handling
    mock_openai_service.get_completion.side_effect = Exception("Test error")
    result = router.classify_multiple_intents("test query")
    assert result == ["general"]