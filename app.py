from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import openai
from agents.agent_router import AgentRouter
from agents.representative_agent import RepresentativeAgent

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Get API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY is None:
    print("Warning: OPENAI_API_KEY not found in environment variables")
else:
    print("API key loaded successfully")
    openai.api_key = OPENAI_API_KEY

# Initialize agents
representative_agent = RepresentativeAgent()
agent_router = AgentRouter()
agent_router.set_representative(representative_agent)

@app.route('/')
def home():
    return "Multi-Agent System (Maria, Sarah, Alex, Mike) is running!"

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_query = data.get("query", "")
        response, category = representative_agent.handle_conversation(user_query)
        return jsonify({
            "response": response,
            "category": category
        })
    except Exception as e:
        print(f"Chat endpoint error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True)

