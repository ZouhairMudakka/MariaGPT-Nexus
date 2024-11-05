import pytest
from agents.sales_agent import SalesAgent

def test_sales_agent_initialization(mock_openai_service, mock_document_manager):
    agent = SalesAgent(mock_openai_service, mock_document_manager)
    assert agent.name == "Sarah"
    assert "products" in agent.specialties
    assert agent.openai_service == mock_openai_service
    assert agent.document_manager == mock_document_manager

def test_get_additional_context(mock_openai_service, mock_document_manager):
    agent = SalesAgent(mock_openai_service, mock_document_manager)
    context = agent.get_additional_context("test query")
    assert "Reference Information" in context
    mock_document_manager.query_knowledge_base.assert_called_once_with("test query", "sales") 