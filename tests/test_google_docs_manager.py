import pytest
from unittest.mock import Mock, patch
from services.google_auth_service import GoogleAuthService, ServiceInitializationError, AuthenticationError
from agents.google_docs_manager import GoogleDocsManager
from config.google_config import REQUIRED_SERVICES

@pytest.fixture
def mock_auth_service():
    auth_service = Mock(spec=GoogleAuthService)
    auth_service.initialize_services.return_value = {
        service: Mock() for service in REQUIRED_SERVICES
    }
    return auth_service

@pytest.fixture
def google_docs_manager(mock_auth_service):
    return GoogleDocsManager(mock_auth_service)

def test_service_initialization(google_docs_manager):
    assert google_docs_manager.validate_services()
    for service_name in REQUIRED_SERVICES:
        assert getattr(google_docs_manager, f"{service_name}_service") is not None

def test_failed_service_initialization(mock_auth_service):
    mock_auth_service.initialize_services.return_value = {}
    with pytest.raises(ServiceInitializationError):
        GoogleDocsManager(mock_auth_service)

def test_service_validation_with_missing_service(google_docs_manager):
    delattr(google_docs_manager, 'docs_service')
    assert not google_docs_manager.validate_services()

def test_service_validation_exception_handling(google_docs_manager):
    setattr(google_docs_manager, 'docs_service', None)
    assert not google_docs_manager.validate_services()

def test_initialization_with_invalid_auth_service():
    auth_service = Mock(spec=GoogleAuthService)
    auth_service.initialize_services.side_effect = AuthenticationError("Invalid credentials")
    
    with pytest.raises(ServiceInitializationError):
        GoogleDocsManager(auth_service)

def test_initialization_with_auth_failure(mock_auth_service):
    mock_auth_service.initialize_services.side_effect = AuthenticationError("Authentication failed")
    
    with pytest.raises(ServiceInitializationError) as exc_info:
        GoogleDocsManager(mock_auth_service)
    assert "Authentication failed" in str(exc_info.value)