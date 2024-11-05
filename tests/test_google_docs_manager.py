import pytest
from agents.google_docs_manager import GoogleDocsManager
from config.settings import settings
import os
from unittest.mock import Mock
from agents.scheduler_agent import SchedulerAgent

@pytest.fixture
def google_docs_manager():
    return GoogleDocsManager()

def test_credentials_exist():
    assert os.path.exists(settings.google_settings['credentials_file']), \
        "Google credentials file not found"

def test_google_drive_connection(google_docs_manager):
    assert google_docs_manager.drive_service is not None
    results = google_docs_manager.get_folder_contents("")  # Root folder
    assert isinstance(results, list) 

def test_initialize_knowledge_base_folder(google_docs_manager):
    folder_name = "Test_Knowledge_Base"
    folder_id = google_docs_manager.initialize_knowledge_base_folder(folder_name)
    assert folder_id is not None
    
    # Verify folder exists
    results = google_docs_manager.get_folder_contents("")  # Root folder
    folder_exists = any(
        item['name'] == folder_name and 
        item['mimeType'] == 'application/vnd.google-apps.folder' 
        for item in results
    )
    assert folder_exists

def test_get_available_slots(google_docs_manager):
    slots = google_docs_manager.get_available_slots(days_ahead=7)
    assert isinstance(slots, list)
    if slots:
        assert all(
            isinstance(slot, dict) and 
            all(key in slot for key in ['id', 'start', 'end', 'summary'])
            for slot in slots
        )

def test_book_appointment_slot(google_docs_manager):
    # First get available slots
    slots = google_docs_manager.get_available_slots(days_ahead=7)
    if not slots:
        pytest.skip("No available slots to test booking")
    
    # Try to book the first available slot
    result = google_docs_manager.book_appointment_slot(
        event_id=slots[0]['id'],
        attendee_email="test@example.com",
        meeting_purpose="Test Meeting"
    )
    assert result is True

def test_scheduler_agent_flow(mock_openai_service, google_docs_manager):
    agent = SchedulerAgent(mock_openai_service, google_docs_manager)
    
    # Mock available slots
    mock_slots = [{
        'id': 'test123',
        'start': '2024-03-20T14:00:00Z',
        'end': '2024-03-20T14:30:00Z',
        'summary': 'Available'
    }]
    google_docs_manager.get_available_slots = Mock(return_value=mock_slots)
    
    # Test scheduling flow
    contact_info = {"email": "test@example.com", "phone": "1234567890"}
    response = agent.handle_scheduling_request(
        "I'd like slot 1 for a product demo",
        contact_info
    )
    assert "booked your appointment" in response