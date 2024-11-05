import pytest
import json
from agents.base_agent import BaseAgent

class TestAgent(BaseAgent):
    def __init__(self, openai_service):
        super().__init__("Test", "Test context", openai_service)

def test_validate_contact_info(mock_openai_service):
    agent = TestAgent(mock_openai_service)
    mock_openai_service.get_completion.return_value = '{"email": "test@example.com", "phone": "1234567890"}'
    result = agent.validate_contact_info("My email is test@example.com and phone is 1234567890")
    assert result["email"] == "test@example.com"
    assert result["phone"] == "1234567890"

def test_validate_meeting_details(mock_openai_service):
    agent = TestAgent(mock_openai_service)
    mock_response = {
        "is_complete": True,
        "date": "2024-03-20",
        "time": "14:00",
        "duration": "1 hour",
        "purpose": "product demo"
    }
    mock_openai_service.get_completion.return_value = json.dumps(mock_response)
    result = agent.validate_meeting_details("Let's meet on March 20th at 2pm for a product demo")
    assert result["is_complete"] is True
    assert result["date"] == "2024-03-20"

def test_conversation_history_management(mock_openai_service):
    agent = TestAgent(mock_openai_service)
    
    # Test adding to conversation history
    query = "test query"
    agent.conversation_history.append({"role": "user", "content": query})
    assert len(agent.conversation_history) == 1
    assert agent.conversation_history[0]["content"] == query
    
    # Test getting conversation history
    history = agent.get_conversation_history()
    assert history == agent.conversation_history
    assert len(history) == 1

def test_is_conversation_end(mock_openai_service):
    agent = TestAgent(mock_openai_service)
    
    # Test positive case
    mock_openai_service.get_completion.return_value = "true"
    assert agent.is_conversation_end("goodbye") is True
    
    # Test negative case
    mock_openai_service.get_completion.return_value = "false"
    assert agent.is_conversation_end("tell me more") is False
    