from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from .base_agent import BaseAgent
from services.openai_service import OpenAIService
from .agent_router import AgentRouter
from evaluators.conversation_evaluator import ConversationEvaluator
from agents.utils.error_handler import handle_agent_errors
from agents.utils.logger import AgentLogger
import json
import os
from .autogen import AutoGenManager, AgentFactory

CONVERSATION_RECORDS_PATH = "conversation_records"

class RepresentativeAgent(BaseAgent):
    def __init__(self, openai_service: OpenAIService, state_manager=None):
        context = """You are Maria, a friendly front-desk representative. 
        You have access to a team of specialized AI agents who can assist with technical support, 
        sales, and scheduling matters. You personally handle HR, finance, and general inquiries.
        Your role is to:
        1. Welcome users and understand their needs
        2. Handle HR, finance, and general questions directly
        3. Coordinate with specialists only for technical, sales, or scheduling matters
        When introducing a specialist, do so naturally and briefly."""
        
        super().__init__("Maria", context, openai_service)
        self.agent_router = AgentRouter(openai_service)
        self.state_manager = state_manager
        self.logger = AgentLogger("RepresentativeAgent")
        self.autogen_manager = AutoGenManager()
        self.conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def handle_conversation_with_autogen(self, query: str) -> Tuple[str, str]:
        try:
            category = self.agent_router.classify_query(query)
            
            # Determine required agents based on category
            required_agents = ["maria"]
            if category in ["technical", "sales", "scheduling"]:
                required_agents.append(category)

            # Initialize AutoGen group chat with required agents
            self.autogen_manager.create_group_chat(required_agents)
            
            # Initiate the conversation
            response = await self.autogen_manager.initiate_chat(query)
            
            return response, category
            
        except Exception as e:
            self.logger.error(f"AutoGen conversation error: {str(e)}")
            return "I apologize, but I'm having trouble processing your request.", "general"

    def handle_valid_contact_info(self, contact_info: Dict[str, Any], category: str, query: str) -> None:
        """Handle validated contact information and schedule follow-ups."""
        try:
            # Get full conversation context for meeting details
            full_context = str(self.conversation_history)
            
            if category == "scheduling":
                # Get available slots for slot-based scheduling
                available_slots = self.google_docs_manager.get_available_slots()
                meeting_details = self.validate_meeting_details(full_context, available_slots)
            else:
                meeting_details = self.validate_meeting_details(full_context)
            
            # Send emails for each department mentioned
            departments = self._extract_requested_departments(full_context)
            for dept in departments:
                self.send_email_notification(
                    contact_info=contact_info,
                    category=dept,
                    meeting_details=meeting_details
                )
            
            # Handle scheduling confirmation
            if category == "scheduling" and meeting_details.get("slot_number"):
                slot_number = int(meeting_details["slot_number"])
                if 0 <= slot_number - 1 < len(available_slots):
                    success = self.google_docs_manager.book_appointment_slot(
                        event_id=available_slots[slot_number - 1]['id'],
                        attendee_email=contact_info['email'],
                        meeting_purpose=meeting_details.get('purpose', 'Business Meeting')
                    )
                    if success:
                        self.send_confirmation_email(contact_info)
                    else:
                        self.send_followup_email(contact_info, category)
            else:
                # Send standard confirmation or followup
                if meeting_details["is_complete"]:
                    self.send_confirmation_email(contact_info)
                else:
                    self.send_followup_email(contact_info, category)
                    
        except Exception as e:
            self.logger.logger.error(f"Error handling contact info: {str(e)}", exc_info=True)

    def _extract_requested_departments(self, conversation: str) -> List[str]:
        """Extract all departments mentioned for meetings."""
        try:
            messages = [{
                "role": "system",
                "content": """Extract all departments mentioned for meetings.
                Return as JSON array: ["marketing", "finance", "hr", "operations", "sales"]
                Only include departments explicitly mentioned."""
            },
            {"role": "user", "content": conversation}]
            
            response = self.openai_service.get_completion(messages)
            return json.loads(response)
        except Exception as e:
            self.logger.logger.error(f"Error extracting departments: {str(e)}")
            return []

    def should_request_contact_info(self, category, contact_info):
        return (category == "scheduling" and 
                not self.validated_contact_info and 
                not contact_info["is_valid"])

    def append_contact_request(self, response, contact_info):
        missing = contact_info.get("missing", ["email", "phone"])
        if "email" in missing and "phone" in missing:
            response += "\n\nTo schedule your meeting, I'll need both your email address and phone number."
        elif "email" in missing:
            response += "\n\nPlease provide your email address to complete the scheduling."
        elif "phone" in missing:
            response += "\n\nPlease provide your phone number to complete the scheduling."
        return response

    def send_email_notification(self, contact_info: Dict[str, Any], category: str, meeting_details: Dict[str, Any]) -> bool:
        try:
            to_email = self.department_emails.get(category, self.department_emails["general"])
            subject = f"New Meeting Request - {category.replace('_', ' ').title()}"
            
            email_content = f"""
            New meeting request from customer:
            Email: {contact_info.get('email')}
            Phone: {contact_info.get('phone')}
            
            Meeting Details:
            Date: {meeting_details.get('date', 'Next week')}
            Time: {meeting_details.get('time', 'To be confirmed')}
            Duration: {meeting_details.get('duration', '1 hour')}
            Purpose: {meeting_details.get('purpose', 'Business discussion')}
            
            Conversation Summary:
            {self.summarize_conversation()}
            """
            
            self.email_logs.append({
                "timestamp": datetime.now().isoformat(),
                "to": to_email,
                "subject": subject,
                "content": email_content,
                "status": "sent"
            })
            
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Email notification error: {str(e)}")
            return False

    def save_email_logs(self):
        try:
            with open("email_logs.json", "w") as f:
                json.dump(self.email_logs, f, indent=2)
        except Exception as e:
            print(f"Error saving email logs: {str(e)}")

    def display_email_logs(self):
        print("\n=== Email Communication Logs ===")
        for log in self.email_logs:
            print(f"\nTimestamp: {log['timestamp']}")
            print(f"To: {log['to']}")
            print(f"Subject: {log['subject']}")
            print("Content:", log['content'])

    def introduce_specialist(self, category: str) -> str:
        specialist_intros = {
            "technical_support": "Let me connect you with Alex, our technical support specialist.",
            "sales_inquiry": "I'll bring in Sarah from our sales team to assist you.",
            "scheduling": "I'll have Mike, our scheduling specialist, help you with that."
        }
        return specialist_intros.get(category, "Let me connect you with the appropriate specialist.")

    def save_conversation_record(self):
        try:
            timestamp = datetime.now().isoformat()
            record = {
                "timestamp": timestamp,
                "conversation": self.conversation_history,
                "summary": self.summarize_conversation(),
                "email_logs": self.email_logs,
                "action_items": self.action_items
            }
            
            with open(f"conversation_records/{timestamp}.json", "w") as f:
                json.dump(record, f, indent=2)
                
        except Exception as e:
            print(f"Error saving conversation record: {str(e)}")

    def summarize_conversation(self) -> str:
        """Generate a summary of the current conversation.
        
        Returns:
            str: Conversation summary or error message
        """
        try:
            if not self.conversation_history:
                return "No conversation to summarize"
                
            messages = [{
                "role": "system",
                "content": "Summarize the conversation in a concise paragraph. Focus on key points and any actions needed."
            },
            {"role": "user", "content": str(self.conversation_history)}]
            
            summary = self.openai_service.get_completion(messages, max_tokens=500)
            return summary if summary else "Error generating summary"
            
        except Exception as e:
            self.logger.logger.error(f"Summary generation error: {str(e)}", exc_info=True)
            return "Error generating summary"

    def welcome(self) -> str:
        """Generate a welcome message for the user.
        
        Returns:
            str: Personalized welcome message
        """
        welcome_message = """Hello! I'm Maria, your virtual assistant. 
        How can I assist you today?"""
        return welcome_message

    def generate_public_summary(self) -> str:
        """Generate a public-friendly summary of the conversation.
        
        Returns:
            str: Formatted conversation summary
        """
        try:
            messages = [{
                "role": "system",
                "content": """Create a brief, professional summary of the conversation. 
                Include key points discussed and any next steps or action items.
                Keep it concise and customer-friendly."""
            },
            {"role": "user", "content": str(self.conversation_history)}]
            
            summary = self.openai_service.get_completion(messages, max_tokens=500)
            return f"Here's a summary of our conversation:\n{summary}"
            
        except Exception as e:
            self.logger.logger.error(f"Public summary generation error: {str(e)}", exc_info=True)
            return "Thank you for your time today. Is there anything else you need help with?"

    def extract_action_items(self) -> None:
        try:
            messages = [{
                "role": "system",
                "content": """Extract action items from the conversation.
                Return as JSON array. If none, return empty array.
                Example: ["Follow up on account balance", "Schedule meeting"]"""
            },
            {"role": "user", "content": str(self.conversation_history)}]
            
            response = self.openai_service.get_completion(messages)
            try:
                self.action_items = json.loads(response)
            except json.JSONDecodeError:
                self.logger.logger.error(f"Invalid JSON in action items: {response}")
                self.action_items = []
                
        except Exception as e:
            self.logger.logger.error(f"Action items extraction error: {str(e)}")
            self.action_items = []

    @handle_agent_errors("I apologize, but I'm having trouble processing your request. Please try again.")
    def evaluate_conversation(self) -> Dict[str, Any]:
        """Evaluate the conversation using ConversationEvaluator."""
        evaluator = ConversationEvaluator()
        evaluation_result, error_metrics = evaluator.evaluate_agent(
            agent_name=self.name,
            conversation_id=self.conversation_id,
            conversation_history=self.conversation_history,
            agent_interactions=self.agent_interactions
        )
        
        if error_metrics:
            self.logger.logger.warning(f"Evaluation completed with errors: {error_metrics}")
            
        # Save evaluation to logs
        self.save_evaluation_log(evaluation_result)
        
        # Send evaluation summary email
        self.send_evaluation_summary(evaluation_result)
        
        return evaluation_result

    def save_evaluation_log(self, evaluation_data: Dict[str, Any]) -> None:
        """Save comprehensive evaluation data including per-agent metrics."""
        try:
            if not os.path.exists("evaluation_logs"):
                os.makedirs("evaluation_logs")
                
            timestamp = datetime.now().isoformat()
            conversation_metrics = self._evaluate_conversation()
            agent_evaluations = self._evaluate_agents()
            user_feedback = self._analyze_user_feedback()
            
            log_entry = {
                "timestamp": timestamp,
                "conversation_id": timestamp,
                "overall_metrics": evaluation_data["metrics"],
                "conversation_metrics": conversation_metrics,
                "agent_evaluations": agent_evaluations,
                "user_feedback": user_feedback,
                "analysis": {
                    "strengths": evaluation_data["analysis"]["strengths"],
                    "areas_for_improvement": evaluation_data["analysis"]["areas_for_improvement"],
                    "user_sentiment": evaluation_data["analysis"]["user_sentiment"],
                    "unmet_needs": evaluation_data["analysis"]["unmet_needs"],
                    "collaboration_notes": evaluation_data["analysis"]["collaboration_notes"]
                },
                "recommendations": evaluation_data["recommendations"],
                "conversation_summary": self.summarize_conversation(),
                "action_items": self.action_items
            }
            
            # Save to daily log file
            date = datetime.now().strftime("%Y-%m-%d")
            log_file = f"evaluation_logs/evaluations_{date}.json"
            
            existing_logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    existing_logs = json.load(f)
                    
            existing_logs.append(log_entry)
            
            with open(log_file, 'w') as f:
                json.dump(existing_logs, f, indent=2)
                
        except Exception as e:
            self.logger.logger.error(f"Error saving evaluation log: {str(e)}", exc_info=True)

    def _evaluate_conversation(self) -> Dict[str, Any]:
        """Evaluate overall conversation metrics."""
        try:
            messages = [{
                "role": "system",
                "content": """Analyze the conversation flow and provide detailed metrics in JSON format:
                {
                    "timing_metrics": {
                        "avg_response_time": float,    # Average time between messages in seconds
                        "total_duration": float,       # Total conversation duration in minutes
                        "resolution_speed": 0-10       # How quickly the main issues were resolved
                    },
                    "flow_metrics": {
                        "conversation_coherence": 0-10, # How well the conversation flowed
                        "context_retention": 0-10,      # How well context was maintained
                        "handoff_smoothness": 0-10,     # Quality of transitions between agents
                        "goal_progression": 0-10        # How effectively the conversation progressed
                    },
                    "outcome_metrics": {
                        "resolution_completeness": 0-10, # How fully issues were resolved
                        "user_satisfaction": 0-10,       # Estimated user satisfaction
                        "follow_up_needed": boolean,     # Whether follow-up is required
                        "escalation_needed": boolean     # Whether escalation is needed
                    }
                }"""
            },
            {"role": "user", "content": str(self.conversation_history)}]
            
            evaluation = self.openai_service.get_completion(messages)
            return json.loads(evaluation)
        except Exception as e:
            self.logger.logger.error(f"Conversation metrics evaluation error: {str(e)}")
            return {}

    def _evaluate_agents(self) -> Dict[str, Any]:
        """Evaluate individual agent performances."""
        try:
            evaluator = ConversationEvaluator()
            agent_evaluations = {}
            
            for msg in self.conversation_history:
                if msg.get("role") == "assistant" and "name" in msg:
                    agent_name = msg["name"]
                    if agent_name not in agent_evaluations:
                        result, error = evaluator.evaluate_agent(
                            agent_name=agent_name,
                            conversation_id=self.conversation_id,
                            conversation_history=self.conversation_history,
                            agent_interactions=self.agent_interactions
                        )
                        agent_evaluations[agent_name] = result
            
            return agent_evaluations
        except Exception as e:
            self.logger.error(f"Error evaluating agents: {str(e)}")
            return {}

    def _analyze_user_feedback(self) -> Dict[str, Any]:
        """Analyze user responses for sentiment and satisfaction."""
        try:
            user_messages = [
                msg for msg in self.conversation_history 
                if msg.get("role") == "user"
            ]
            
            messages = [{
                "role": "system",
                "content": """Analyze user messages for feedback indicators. Return in JSON format:
                {
                    "sentiment_analysis": {
                        "overall_sentiment": -1.0 to 1.0,  # Sentiment score
                        "sentiment_progression": [],        # How sentiment changed
                        "key_moments": []                  # Important interaction points
                    },
                    "satisfaction_indicators": {
                        "explicit_feedback": [],           # Direct feedback statements
                        "implicit_feedback": [],           # Indirect feedback indicators
                        "pain_points": [],                # User frustrations
                        "positive_points": []             # User satisfactions
                    },
                    "engagement_metrics": {
                        "responsiveness": 0-10,           # User engagement level
                        "cooperation": 0-10,              # User cooperation level
                        "clarity": 0-10                   # User communication clarity
                    }
                }"""
            },
            {"role": "user", "content": str(user_messages)}]
            
            evaluation = self.openai_service.get_completion(messages)
            return json.loads(evaluation)
        except Exception as e:
            self.logger.logger.error(f"User feedback analysis error: {str(e)}")
            return {}

    def send_evaluation_summary(self, evaluation_data: Dict[str, Any]) -> None:
        """Send evaluation summary email at the end of conversation."""
        try:
            conversation_summary = self.summarize_conversation()
            agent_evaluations = self._evaluate_agents()
            
            email_content = f"""
Conversation Evaluation Summary

Timestamp: {datetime.now().isoformat()}

Overall Metrics:
- Needs Met: {evaluation_data['metrics']['needs_met']}/10
- Agent Collaboration: {evaluation_data['metrics']['agent_collaboration']}/10
- Response Quality: {evaluation_data['metrics']['response_quality']}/10
- Efficiency: {evaluation_data['metrics']['efficiency']}/10
- Overall Score: {evaluation_data['metrics']['overall_score']}/10

Analysis:
Strengths:
{chr(10).join(f'- {s}' for s in evaluation_data['analysis']['strengths'])}

Areas for Improvement:
{chr(10).join(f'- {a}' for a in evaluation_data['analysis']['areas_for_improvement'])}

User Sentiment: {evaluation_data['analysis']['user_sentiment']}

Conversation Summary:
{conversation_summary}

Individual Agent Evaluations:
{self._format_agent_evaluations(agent_evaluations)}

Action Items:
{chr(10).join(f'- {item}' for item in self.action_items)}

Recommendations:
{chr(10).join(f'- {r}' for r in evaluation_data['recommendations'])}
"""

            self._send_email(
                to="hr@mudakka.com",
                subject=f"Conversation Evaluation Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                content=email_content,
                from_email="maria.gpt@mudakka.com"
            )
            
            # Log the email
            self.email_logs.append({
                "timestamp": datetime.now().isoformat(),
                "to": "hr@mudakka.com",
                "subject": f"Conversation Evaluation Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "content": email_content
            })
            
        except Exception as e:
            self.logger.logger.error(f"Error sending evaluation summary: {str(e)}")

    def _format_agent_evaluations(self, agent_evaluations: Dict[str, Any]) -> str:
        """Format agent evaluations for email content."""
        formatted = []
        for agent, metrics in agent_evaluations.items():
            formatted.append(f"\n{agent}:")
            for category, scores in metrics.items():
                formatted.append(f"\n{category.replace('_', ' ').title()}:")
                for metric, score in scores.items():
                    formatted.append(f"- {metric}: {score}/10")
        return "\n".join(formatted)

    def is_conversation_ended(self) -> bool:
        """Detect if the conversation has naturally concluded."""
        try:
            messages = [{
                "role": "system",
                "content": """Analyze if the conversation has naturally concluded. Consider:
                1. User's final response indicates completion
                2. All main topics/issues were addressed
                3. No pending questions or actions
                Return JSON: {"ended": boolean, "reason": "explanation"}"""
            },
            {"role": "user", "content": str(self.conversation_history[-3:])}]
            
            response = self.openai_service.get_completion(messages)
            result = json.loads(response)
            return result["ended"]
        except Exception as e:
            self.logger.error(f"Error detecting conversation end: {str(e)}")
            return False

    def handle_conversation_end(self):
        """Handle end of conversation tasks."""
        try:
            # Extract action items
            self.extract_action_items()
            
            # Generate final evaluation
            evaluation_data = self.evaluate_conversation()
            
            # Send evaluation email to HR
            self.send_evaluation_summary(evaluation_data)
            
            # Save conversation record
            self.save_conversation_record()
            
            # Generate user satisfaction survey
            survey_link = self.generate_satisfaction_survey()
            
            return f"Thank you for your time. {survey_link}"
        except Exception as e:
            self.logger.error(f"Error handling conversation end: {str(e)}")
            return "Thank you for your time."

    def validate_contact_info(self, text: str) -> Dict[str, Any]:
        try:
            messages = [{
                "role": "system",
                "content": """Extract contact information from the text.
                Return as JSON: {
                    "email": "extracted email or null",
                    "phone": "extracted phone or null",
                    "is_valid": false
                }
                Do not include any markdown formatting."""
            },
            {"role": "user", "content": text}]
            
            response = self.openai_service.get_completion(messages)
            contact_info = json.loads(response.replace('```json', '').replace('```', '').strip())
            
            # Validate email and phone
            contact_info["is_valid"] = bool(contact_info.get("email") or contact_info.get("phone"))
            return contact_info
            
        except Exception as e:
            self.logger.logger.error(f"Contact validation error: {str(e)}")
            return {"email": None, "phone": None, "is_valid": False}

    def get_specialist_name(self, category: str) -> str:
        """Get specialist name based on category."""
        specialist_names = {
            'technical_support': 'Alex',
            'sales_inquiry': 'Sarah',
            'scheduling': 'Mike',
            'general': 'Maria'
        }
        return specialist_names.get(category, 'Unknown')
