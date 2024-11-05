import pytest
import json
from agents.scheduler_agent import SchedulerAgent

def test_slot_booking(mock_openai_service, google_docs_manager):
    agent = SchedulerAgent(mock_openai_service, google_docs_manager)
    
    # Mock available slots
    mock_slots = [{
        'id': 'test123',
        'start': '2024-03-20T14:00:00Z',
        'end': '2024-03-20T14:30:00Z',
        'summary': 'Available'
    }]
    google_docs_manager.get_available_slots.return_value = mock_slots
    
    # Mock OpenAI response for meeting validation
    mock_openai_service.get_completion.return_value = json.dumps({
        "is_complete": True,
        "slot_number": "1",
        "purpose": "Test Meeting"
    })
    
    # Mock successful booking
    google_docs_manager.book_appointment_slot.return_value = True
    
    result = agent.handle_scheduling_request(
        query="I want slot 1 for a Test Meeting",
        contact_info={'email': 'test@example.com'}
    )
    assert "Great! I've booked your appointment" in result

def test_slot_booking_invalid_slot(mock_openai_service, google_docs_manager):
    agent = SchedulerAgent(mock_openai_service, google_docs_manager)
    mock_slots = [{
        'id': 'test123',
        'start': '2024-03-20T14:00:00Z',
        'end': '2024-03-20T14:30:00Z',
        'summary': 'Available'
    }]
    google_docs_manager.get_available_slots.return_value = mock_slots
    
    # Mock OpenAI response for invalid slot
    mock_openai_service.get_completion.return_value = json.dumps({
        "is_complete": True,
        "slot_number": "999",
        "purpose": "Test Meeting"
    })
    
    result = agent.handle_scheduling_request(
        query="I want slot 999 for a Test Meeting",
        contact_info={'email': 'test@example.com'}
    )
    assert "error booking your appointment" in result

def test_no_available_slots(mock_openai_service, google_docs_manager):
    agent = SchedulerAgent(mock_openai_service, google_docs_manager)
    google_docs_manager.get_available_slots.return_value = []
    
    result = agent.handle_scheduling_request(
        query="I want to schedule a meeting",
        contact_info={'email': 'test@example.com'}
    )
    assert "no available slots" in result

def test_no_slot_selected(mock_openai_service, google_docs_manager):
    agent = SchedulerAgent(mock_openai_service, google_docs_manager)
    mock_slots = [{
        'id': 'test123',
        'start': '2024-03-20T14:00:00Z',
        'end': '2024-03-20T14:30:00Z',
        'summary': 'Available'
    }]
    google_docs_manager.get_available_slots.return_value = mock_slots
    
    # Mock OpenAI response with no slot selected
    mock_openai_service.get_completion.return_value = json.dumps({
        "is_complete": False,
        "slot_number": None,
        "purpose": "Test Meeting"
    })
    
    result = agent.handle_scheduling_request(
        query="I need to schedule a meeting",
        contact_info={'email': 'test@example.com'}
    )
    assert "Please let me know which slot you'd prefer" in result