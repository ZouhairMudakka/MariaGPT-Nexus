import pytest
import json
from unittest.mock import Mock, patch
from agents.agent_router import AgentRouter
from agents.scheduler_agent import SchedulerAgent
from agents.representative_agent import RepresentativeAgent
from agents.state_manager import StateManager
import os
from datetime import datetime
from dotenv import load_dotenv
from agents.openai_service import OpenAIService

@pytest.fixture
def mock_chat_environment(mock_openai_service, google_docs_manager):
    router = AgentRouter(mock_openai_service)
    router.scheduler_agent = SchedulerAgent(mock_openai_service, google_docs_manager)
    router.representative_agent = RepresentativeAgent(mock_openai_service)
    return router

@pytest.fixture
def mock_state_manager():
    return StateManager()

def test_scheduling_conversation_flow(mock_chat_environment, mock_openai_service, google_docs_manager):
    # Mock the initial classification
    mock_openai_service.get_completion.side_effect = [
        "scheduling",  # First call - classify query
        json.dumps({   # Second call - validate meeting details
            "is_complete": False,
            "slot_number": None,
            "purpose": None
        }),
        json.dumps({   # Third call - validate meeting details with slot
            "is_complete": True,
            "slot_number": "1",
            "purpose": "Test Meeting"
        })
    ]
    
    # Mock available slots
    mock_slots = [{
        'id': 'test123',
        'start': '2024-03-20T14:00:00Z',
        'end': '2024-03-20T14:30:00Z',
        'summary': 'Available'
    }]
    google_docs_manager.get_available_slots.return_value = mock_slots
    google_docs_manager.book_appointment_slot.return_value = True
    
    # Simulate conversation flow
    conversation = [
        "I need to schedule a meeting",
        "I want slot 1 for a Test Meeting"
    ]
    
    contact_info = {'email': 'test@example.com'}
    
    for message in conversation:
        response = mock_chat_environment.route_query(
            message,
            contact_info=contact_info
        )
        assert response is not None
        
    # Verify final booking was successful
    assert "Great! I've booked your appointment" in response 

def test_technical_support_flow(mock_chat_environment, mock_openai_service):
    # Mock the initial classification
    mock_openai_service.get_completion.side_effect = [
        "technical_support",  # First call - classify query
        json.dumps({   # Second call - validate technical details
            "is_complete": True,
            "issue_type": "login",
            "severity": "medium"
        })
    ]
    
    conversation = [
        "I can't log into my account",
        "I keep getting an error message"
    ]
    
    contact_info = {'email': 'test@example.com'}
    
    for message in conversation:
        response = mock_chat_environment.route_query(
            message,
            contact_info=contact_info
        )
        assert response is not None
        assert "[Alex]" in response or "technical support" in response.lower()

def test_conversation_end_detection(mock_chat_environment, mock_openai_service):
    mock_openai_service.get_completion.return_value = "general"
    
    # Test explicit exit commands
    assert mock_chat_environment.representative_agent.is_conversation_end("quit")
    assert mock_chat_environment.representative_agent.is_conversation_end("exit")
    
    # Test natural conversation end
    response = mock_chat_environment.route_query("Thank you, goodbye!")
    assert "goodbye" in response.lower()

def test_public_summary_generation(mock_chat_environment, mock_openai_service):
    agent = mock_chat_environment.representative_agent
    
    # Setup conversation history
    conversation = [
        {"role": "user", "content": "I need technical help"},
        {"role": "assistant", "content": "I can help with that"},
        {"role": "user", "content": "Thanks, goodbye"}
    ]
    agent.conversation_history.extend(conversation)
    
    mock_openai_service.get_completion.return_value = "Technical support inquiry resolved"
    summary = agent.generate_public_summary()
    assert summary is not None
    assert len(summary) > 0

def test_action_items_extraction(mock_chat_environment, mock_openai_service):
    agent = mock_chat_environment.representative_agent
    
    # Setup conversation with action items
    conversation = [
        {"role": "user", "content": "Please schedule a follow-up next week"},
        {"role": "assistant", "content": "I'll help schedule that"},
    ]
    agent.conversation_history.extend(conversation)
    
    mock_openai_service.get_completion.return_value = json.dumps([
        "Schedule follow-up meeting",
        "Send documentation"
    ])
    
    action_items = agent.extract_action_items()
    assert isinstance(action_items, list)
    assert len(action_items) > 0

def test_specialist_name_assignment(mock_chat_environment, mock_openai_service):
    # Test different specialist assignments
    categories = {
        "technical_support": "Alex",
        "sales_inquiry": "Sarah",
        "scheduling": "Mike",
        "general": "Maria"
    }
    
    for category, expected_name in categories.items():
        mock_openai_service.get_completion.return_value = category
        response = mock_chat_environment.route_query("test query")
        assert response is not None
        # Verify specialist name appears in response or metadata

def test_save_conversation(mock_chat_environment, mock_openai_service, tmp_path):
    agent = mock_chat_environment.representative_agent
    agent.conversation_history = [
        {"role": "user", "content": "Test message"},
        {"role": "assistant", "content": "Test response"}
    ]
    
    records_dir = tmp_path / "conversation_records"
    records_dir.mkdir()
    
    with patch('os.makedirs'), patch('builtins.open', create=True) as mock_open:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        mock_chat_environment.save_conversation(agent.conversation_history)
        mock_open.assert_called_once_with(f"conversation_records/{timestamp}.json", 'w', encoding='utf-8')

def test_multiple_intent_handling(mock_chat_environment, mock_openai_service):
    # Test handling multiple intents (e.g., sales + scheduling)
    mock_openai_service.get_completion.side_effect = [
        "sales_inquiry, scheduling",
        json.dumps({"product": "enterprise", "interest": "high"}),
        json.dumps({"is_complete": True, "slot_number": "1", "purpose": "Product Demo"})
    ]
    
    response = mock_chat_environment.route_query(
        "I want to schedule a demo of your enterprise product",
        contact_info={'email': 'test@example.com'}
    )
    assert response is not None
    assert any(name in response for name in ["Sarah", "Mike"])

def test_error_recovery(mock_chat_environment, mock_openai_service):
    # Test system recovery from errors
    mock_openai_service.get_completion.side_effect = Exception("API Error")
    
    response = mock_chat_environment.route_query("Test message")
    assert "apologize" in response.lower()
    assert "error" in response.lower()

def test_conversation_state_management(mock_chat_environment, mock_state_manager):
    # Test state transitions
    states = ["initial", "gathering_info", "processing", "followup"]
    
    for state in states:
        mock_state_manager.current_state = state
        response = mock_chat_environment.route_query(
            "Test message",
            state=state
        )
        assert response is not None

def test_specialist_handoff(mock_chat_environment, mock_openai_service):
    # Test handoff between specialists
    mock_openai_service.get_completion.side_effect = [
        "technical_support",  # First query classification
        "scheduling"         # Second query classification
    ]
    
    # Technical support query
    response1 = mock_chat_environment.route_query("I have a technical issue")
    assert "[Alex]" in response1 or "technical support" in response1.lower()
    
    # Scheduling query
    response2 = mock_chat_environment.route_query("Can we schedule a follow-up?")
    assert "[Mike]" in response2 or "schedule" in response2.lower()

def test_email_log_saving(mock_chat_environment, mock_openai_service, tmp_path):
    agent = mock_chat_environment.representative_agent
    
    # Setup email logs
    email_logs = [
        {"to": "user@example.com", "subject": "Meeting Confirmation", "sent": True},
        {"to": "support@example.com", "subject": "Technical Issue", "sent": True}
    ]
    agent.email_logs = email_logs
    
    logs_path = tmp_path / "email_logs.json"
    with patch('builtins.open', create=True) as mock_open:
        agent.save_email_logs()
        mock_open.assert_called_once_with("email_logs.json", "w")

def test_contact_info_validation_flow(mock_chat_environment, mock_openai_service):
    # Test the complete contact info validation flow
    mock_openai_service.get_completion.side_effect = [
        "scheduling",  # Initial classification
        json.dumps({   # Contact info validation
            "email": None,
            "phone": None,
            "is_valid": False
        }),
        json.dumps({   # Second attempt with valid info
            "email": "test@example.com",
            "phone": "1234567890",
            "is_valid": True
        })
    ]
    
    # First attempt without contact info
    response1 = mock_chat_environment.route_query("Schedule a meeting")
    assert "provide" in response1.lower() and "contact" in response1.lower()
    
    # Second attempt with contact info
    response2 = mock_chat_environment.route_query(
        "My email is test@example.com and phone is 1234567890"
    )
    assert "schedule" in response2.lower()

def test_conversation_context_persistence(mock_chat_environment, mock_openai_service):
    # Test that context is maintained across multiple interactions
    mock_openai_service.get_completion.side_effect = [
        "technical_support",
        "Technical issue noted",
        "scheduling",
        "Scheduling follow-up"
    ]
    
    # Initial technical support query
    response1 = mock_chat_environment.route_query("I have a problem with login")
    assert "technical" in response1.lower()
    
    # Follow-up query should maintain context
    response2 = mock_chat_environment.route_query("Can we schedule a call about this?")
    assert "schedule" in response2.lower()
    
    # Verify conversation history
    history = mock_chat_environment.representative_agent.get_conversation_history()
    assert len(history) >= 4  # Should include both interactions and responses

def test_invalid_json_handling(mock_chat_environment, mock_openai_service):
    # Test handling of invalid JSON responses from OpenAI
    mock_openai_service.get_completion.side_effect = [
        "scheduling",
        "Invalid JSON response",  # Simulating corrupted JSON
        json.dumps({  # Recovery response
            "is_complete": False,
            "slot_number": None,
            "purpose": None
        })
    ]
    
    response = mock_chat_environment.route_query("Schedule a meeting")
    assert "error" in response.lower() or "try again" in response.lower()

def test_concurrent_specialist_handling(mock_chat_environment, mock_openai_service):
    # Test handling multiple specialists in same conversation
    mock_openai_service.get_completion.side_effect = [
        "sales_inquiry, technical_support",  # Multiple intents
        "Product information provided",      # Sales response
        "Technical solution provided"        # Tech support response
    ]
    
    response = mock_chat_environment.route_query(
        "I need help with your enterprise product features"
    )
    
    # Should include responses from both specialists
    assert any(name in response for name in ["Sarah", "Alex"])
    assert "product" in response.lower() or "technical" in response.lower()

def test_knowledge_base_integration(mock_chat_environment, mock_openai_service, mock_document_manager):
    # Test knowledge base queries
    mock_openai_service.get_completion.side_effect = [
        "sales_inquiry",
        "Product information retrieved"
    ]
    mock_document_manager.query_knowledge_base.return_value = "Product specs..."
    
    response = mock_chat_environment.route_query("Tell me about your enterprise plan")
    assert "Product" in response
    assert mock_document_manager.query_knowledge_base.called

def get_available_test_functions():
    """Return a formatted string of available test functionalities"""
    test_functions = {
        "Scheduling": [
            "Book appointments",
            "Check available slots",
            "Reschedule meetings"
        ],
        "Technical Support": [
            "Account issues",
            "Technical problems",
            "Product assistance"
        ],
        "Sales": [
            "Product information",
            "Pricing inquiries",
            "Demo scheduling"
        ],
        "General": [
            "Contact info validation",
            "Multi-intent queries",
            "Conversation history"
        ],
        "Error Handling": [
            "API failures",
            "Invalid responses",
            "Connection timeouts",
            "Rate limiting",
            "Data validation errors"
        ],
        "State Management": [
            "Context switching",
            "Conversation persistence",
            "Session management",
            "Agent handoffs"
        ],
        "Data Management": [
            "Conversation logging",
            "Email tracking",
            "Document handling",
            "Knowledge base queries"
        ],
        "Security & Validation": [
            "Input sanitization",
            "Contact info verification",
            "Session validation",
            "Access control"
        ]
    }
    
    output = "\nAvailable Test Functions:\n" + "="*22 + "\n\n"
    for category, functions in test_functions.items():
        output += f"{category}:\n"
        for func in functions:
            output += f"  - {func}\n"
        output += "\n"
    return output

def display_test_chat_info():
    """Display initial test chat information"""
    print("\nTest Chat Environment")
    print("=" * 20)
    print("\nThis is a test environment for the multi-agent chat system.")
    print("Type 'quit' or 'exit' to end the conversation.")
    print("Type 'help' to see available test functions.")
    print("\nNote: This is a test environment and no actual services are called.")
    print(get_available_test_functions())

def simulate_conversation_flow(mock_chat_environment, messages, expected_responses):
    """Helper to simulate a complete conversation flow"""
    conversation_history = []
    for msg, expected in zip(messages, expected_responses):
        response = mock_chat_environment.route_query(msg)
        assert any(exp in response.lower() for exp in expected)
        conversation_history.append({"message": msg, "response": response})
    return conversation_history

def verify_specialist_response(response, specialist_name, expected_content):
    """Helper to verify specialist responses"""
    assert f"[{specialist_name}]" in response or specialist_name.lower() in response.lower()
    assert any(content in response.lower() for content in expected_content)

def main():
    # Initialize services and agents
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    openai_service = OpenAIService(api_key=api_key)
    
    # Display test environment information
    display_test_chat_info()
    
    # Rest of the main function...