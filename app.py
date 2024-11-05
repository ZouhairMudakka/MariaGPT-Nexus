from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from agents.agent_router import AgentRouter
from agents.representative_agent import RepresentativeAgent
from services.openai_service import OpenAIService
from agents.autogen.workflows.conversation import ConversationWorkflow
from agents.evaluation_metrics import ConversationEvaluator, EvaluationStorage
from utils.logger import Logger

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Initialize services and components
openai_service = OpenAIService(api_key=os.getenv("OPENAI_API_KEY"))
logger = Logger(name="mariagpt")
evaluator = ConversationEvaluator(log_dir="evaluation_logs")
evaluation_storage = EvaluationStorage()

# Initialize workflow
conversation_workflow = ConversationWorkflow(
    group_chat=None,  # Will be set per conversation
    evaluator=evaluator,
    evaluation_storage=evaluation_storage,
    openai_service=openai_service,
    logger=logger
)

# Initialize agents
representative_agent = RepresentativeAgent(
    openai_service=openai_service,
    conversation_workflow=conversation_workflow
)
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

