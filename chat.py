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

def main():
    # Initialize OpenAIService first
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    openai_service = OpenAIService(api_key=api_key)
    
    # Initialize state manager
    from agents.state_manager import StateManager
    state_manager = StateManager()
    
    # Pass both openai_service and state_manager to RepresentativeAgent
    agent = RepresentativeAgent(openai_service=openai_service, state_manager=state_manager)
    
    print("Multi-Agent Chatbot (type 'quit' to exit)")
    print("-" * 40)
    
    # Display welcome message
    display_message(agent.name, agent.welcome())
    
    while True:
        user_message = input("You: ")
        
        # Check for conversation end
        if user_message.lower() in ['quit', 'exit'] or agent.is_conversation_end(user_message):
            # Generate and show public summary
            display_message(agent.name, agent.generate_public_summary())
            
            # Extract and save action items
            agent.extract_action_items()
            
            # Save complete conversation record
            save_conversation(agent.conversation_history)
            
            print(f"\n[{agent.name}]: Goodbye! Have a great day!")
            break
        
        # Get response from appropriate specialist
        response, category = agent.handle_conversation(user_message)
        
        # Get specialist name based on category
        specialist_names = {
            'technical_support': 'Alex',
            'sales_inquiry': 'Sarah',
            'scheduling': 'Mike',
            'general': 'Maria'
        }
        specialist_name = specialist_names.get(category, 'Unknown')
        
        display_message(specialist_name, response)

if __name__ == "__main__":
    main()
