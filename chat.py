import os
import sys
from dotenv import load_dotenv
from datetime import datetime
import json
import logging

# Get the absolute path to the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))
# Add it to Python path
sys.path.insert(0, project_root)

from services.openai_service import OpenAIService
from agents.representative_agent import RepresentativeAgent
from services.google_auth_service import GoogleAuthService, AuthenticationError, ServiceInitializationError
from agents.google_docs_manager import GoogleDocsManager
from config.google_config import GOOGLE_API_SCOPES, AUTH_SETTINGS
from utils.logger import Logger
from agents.evaluation_metrics import ConversationEvaluator, EvaluationStorage
from agents.autogen.workflows.conversation import ConversationWorkflow

def display_message(agent_name: str, message: str):
    # Remove the agent name if it appears in the message
    if message.startswith(f"[{agent_name}]:"):
        message = message.replace(f"[{agent_name}]:", "").strip()
    print(f"[{agent_name}]: {message}")

def save_conversation(conversation_history):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Replace : with _
    filename = f"conversation_records/{timestamp}.json"
    
    # Ensure the directory exists
    os.makedirs("conversation_records", exist_ok=True)
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(conversation_history, f, indent=2)
    except Exception as e:
        print(f"Error saving conversation record: {e}")

def initialize_services():
    try:
        # Initialize Google Auth Service
        auth_service = GoogleAuthService(
            credentials_file=AUTH_SETTINGS['credentials_file'],
            token_file=AUTH_SETTINGS['token_file'],
            scopes=GOOGLE_API_SCOPES
        )
        
        # Initialize Google Docs Manager with auth service
        google_docs_manager = GoogleDocsManager(auth_service)
        
        if not google_docs_manager.validate_services():
            raise ServiceInitializationError("Failed to validate Google services")
            
        return google_docs_manager
    except (ImportError, AuthenticationError, ServiceInitializationError) as e:
        logging.error(f"Failed to initialize services: {str(e)}")
        raise

async def main():
    # Initialize services
    load_dotenv()
    openai_service = OpenAIService(api_key=os.getenv("OPENAI_API_KEY"))
    logger = Logger(name="mariagpt")
    evaluator = ConversationEvaluator(log_dir="evaluation_logs")
    evaluation_storage = EvaluationStorage()
    
    # Initialize workflow
    conversation_workflow = ConversationWorkflow(
        group_chat=None,
        evaluator=evaluator,
        evaluation_storage=evaluation_storage,
        openai_service=openai_service,
        logger=logger
    )
    
    # Initialize agent with workflow
    agent = RepresentativeAgent(
        openai_service=openai_service,
        conversation_workflow=conversation_workflow
    )
    
    print("Multi-Agent Chatbot (type 'quit' to exit)")
    print("-" * 40)
    
    # Display welcome message
    display_message(agent.name, agent.welcome())
    
    while True:
        user_message = input("You: ")
        
        if user_message.lower() in ['quit', 'exit']:
            # Handle conversation end using workflow
            end_message = await conversation_workflow.handle_conversation_end()
            display_message(agent.name, end_message)
            break
            
        # Get response using workflow patterns
        response, category = agent.handle_conversation(user_message)
        specialist_name = agent.get_specialist_name(category)
        display_message(specialist_name, response)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

if __name__ == "__main__":
    main()
