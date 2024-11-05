import pytest
from datetime import datetime
import json
import os
from unittest.mock import Mock
from agents.representative_agent import RepresentativeAgent

def test_representative_agent_initialization(mock_openai_service):
    agent = RepresentativeAgent(mock_openai_service)
    assert agent.name == "Maria"
    assert "technical_support" in agent.department_emails
    assert agent.sender_email == "maria.gpt@mudakka.com"
    assert agent.reply_to_email == "noreply@mudakka.com"

def test_handle_conversation(mock_openai_service):
    agent = RepresentativeAgent(mock_openai_service)
    mock_openai_service.get_completion.return_value = "technical_support"
    response, category = agent.handle_conversation("I need technical help")
    assert category == "technical_support"
    assert len(agent.conversation_history) == 2

def test_should_request_contact_info(mock_openai_service):
    agent = RepresentativeAgent(mock_openai_service)
    contact_info = {"is_valid": False}
    assert agent.should_request_contact_info("scheduling", contact_info) is True
    assert agent.should_request_contact_info("general", contact_info) is False

def test_append_contact_request(mock_openai_service):
    agent = RepresentativeAgent(mock_openai_service)
    response = "Initial response"
    contact_info = {"missing": ["email", "phone"]}
    result = agent.append_contact_request(response, contact_info)
    assert "email address" in result
    assert "phone number" in result

def test_save_conversation_record(mock_openai_service, tmp_path, monkeypatch):
    agent = RepresentativeAgent(mock_openai_service)
    agent.conversation_history = [
        {"role": "user", "content": "test message"},
        {"role": "assistant", "content": "test response"}
    ]
    
    # Create conversation_records directory in tmp_path
    records_dir = tmp_path / "conversation_records"
    records_dir.mkdir()
    
    # Patch the conversation records path
    monkeypatch.setattr("agents.representative_agent.CONVERSATION_RECORDS_PATH", str(records_dir))
    
    agent.save_conversation_record()
    saved_files = list(records_dir.glob("*.json"))
    assert len(saved_files) == 1

def test_validate_contact_info_with_markdown(mock_openai_service):
    agent = RepresentativeAgent(mock_openai_service)
    mock_openai_service.get_completion.return_value = '''```json
    {
        "email": "test@example.com",
        "phone": "1234567890",
        "name": "Test User",
        "is_valid": true
    }
    ```'''
    
    result = agent.validate_contact_info("Test conversation")
    assert result["email"] == "test@example.com"
    assert result["phone"] == "1234567890"
    assert result["is_valid"] is True