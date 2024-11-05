import pytest
from agents.base_router import BaseRouter

class TestRouter(BaseRouter):
    def classify_query(self, query):
        return "test_category"

def test_router_initialization(mock_openai_service):
    router = TestRouter(mock_openai_service)
    assert isinstance(router.agent_interactions, set)
    assert router.openai_service == mock_openai_service

def test_get_completion(mock_openai_service):
    router = TestRouter(mock_openai_service)
    messages = [{"role": "user", "content": "test"}]
    response = router._get_completion(messages)
    assert response == "Test response"
    mock_openai_service.get_completion.assert_called_once() 