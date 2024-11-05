from dotenv import load_dotenv
import os
import openai
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API Key and make it available for import
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY is None:
    raise ValueError("OPENAI_API_KEY not found in environment variables")
else:
    # Optional: Print a secure confirmation without exposing the key
    print("API key loaded successfully")

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Google API Configuration
GOOGLE_CREDENTIALS_FILE = Path("multiagent_demo_credentials.json")
GOOGLE_TOKEN_FILE = Path("token.pickle")
RESOURCES_FOLDER_NAME = "MudakkaBot_Resources"

# Validate Google credentials
if not GOOGLE_CREDENTIALS_FILE.exists():
    print(f"Warning: Google credentials file not found at {GOOGLE_CREDENTIALS_FILE}")

# Make sure to export the variable
__all__ = ['OPENAI_API_KEY', 'GOOGLE_CREDENTIALS_FILE', 'GOOGLE_TOKEN_FILE', 'RESOURCES_FOLDER_NAME']

