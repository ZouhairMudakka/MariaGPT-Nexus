from typing import Dict, List, Optional, Tuple, Any
import asyncio
import json
import os
from datetime import datetime
from dataclasses import dataclass
from ..config import AutoGenConfig
from ...utils.logger import Logger, MetricsLogger
from ....services.openai_service import OpenAIService
from ...evaluation_metrics import (
    ConversationEvaluator, 
    ConversationMetrics, 
    EvaluationStorage,
    MetricsValidator,
    TimingMetrics,
    AgentMetrics,
    ErrorMetrics
)
from .exceptions import DataProcessingError
from functools import wraps
from autogen import GroupChat
from ...utils.error_handler import handle_agent_errors
from ...utils.file_manager import FileManager
from .recovery_strategies import RecoveryStrategy

class ConversationWorkflow:
    def __init__(self, 
                 group_chat: GroupChat,
                 evaluator: 'ConversationEvaluator',
                 evaluation_storage: 'EvaluationStorage',
                 openai_service: 'OpenAIService',
                 logger: 'Logger'):
        """Initialize ConversationWorkflow."""
        self.group_chat = group_chat
        self.evaluator = evaluator
        self.evaluation_storage = evaluation_storage
        self.openai_service = openai_service
        self.logger = logger
        self.conversation_history = []
        self.error_handler = ErrorHandler(self.logger)
        self.recovery_states = {}
        self.recovery_strategy = RecoveryStrategy(self.logger)

    @handle_agent_errors("I apologize, but I'm having trouble processing your request. Please try again.")
    async def evaluate_conversation(self) -> Dict[str, Any]:
        """Evaluate the conversation using ConversationEvaluator."""
        try:
            # Get base metrics from evaluator
            evaluation_result, error_metrics = self.evaluator.evaluate_agent(
                agent_name=self.group_chat.agents[0].name,
                conversation_id=str(id(self)),
                conversation_history=self.conversation_history,
                agent_interactions=self._get_agent_interactions()
            )

            # Get flow metrics using pattern from ConversationEvaluator
            flow_metrics = self.evaluator.evaluate_conversation_flow(self.conversation_history)
            evaluation_result.update(flow_metrics)

            # Calculate detailed metrics using RepresentativeAgent pattern
            detailed_metrics = await self._evaluate_detailed_metrics()
            evaluation_result.update(detailed_metrics)

            if error_metrics:
                self.logger.warning(f"Evaluation completed with errors: {error_metrics}")

            # Save evaluation to logs
            await self.save_evaluation_log(evaluation_result)
            
            # Send evaluation summary
            await self.send_evaluation_summary(evaluation_result)
            
            return evaluation_result
            
        except Exception as e:
            self.logger.error(f"Conversation evaluation error: {str(e)}")
            return {}

    async def _evaluate_detailed_metrics(self) -> Dict[str, Any]:
        """Evaluate detailed conversation metrics using RepresentativeAgent pattern."""
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
            
            # Get completion from OpenAI with specific settings
            response = await self.openai_service.get_completion(
                messages,
                model="gpt-4",  # Using GPT-4 for better analysis
                temperature=0.3  # Lower temperature for more consistent evaluations
            )
            
            try:
                metrics = json.loads(response)
                
                # Calculate additional timing metrics
                timestamps = [msg.get("timestamp") for msg in self.conversation_history 
                            if msg.get("timestamp")]
                if len(timestamps) >= 2:
                    start_time = datetime.fromisoformat(timestamps[0])
                    end_time = datetime.fromisoformat(timestamps[-1])
                    metrics["timing_metrics"]["total_duration"] = (end_time - start_time).total_seconds() / 60
                    
                    # Calculate average response time
                    response_times = []
                    for i in range(1, len(timestamps)):
                        t1 = datetime.fromisoformat(timestamps[i-1])
                        t2 = datetime.fromisoformat(timestamps[i])
                        response_times.append((t2 - t1).total_seconds())
                    
                    if response_times:
                        metrics["timing_metrics"]["avg_response_time"] = sum(response_times) / len(response_times)
                
                return metrics
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing metrics JSON: {str(e)}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Error evaluating detailed metrics: {str(e)}")
            return {}

    def _get_agent_interactions(self) -> List[Dict[str, Any]]:
        """Extract agent interaction patterns."""
        interactions = []
        for msg in self.conversation_history:
            if msg.get("agent"):
                interactions.append({
                    "agent": msg["agent"],
                    "timestamp": msg.get("timestamp", datetime.now().isoformat()),
                    "response_time": msg.get("response_time", 0),
                    "category": msg.get("category", "general"),
                    "content": msg["content"]
                })
        return interactions

    async def is_conversation_ended(self) -> bool:
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
            
            response = await self.group_chat.process_message(
                message=str(messages),
                sender=self.group_chat.agents[0],
                max_rounds=1
            )
            
            result = json.loads(response)
            return result["ended"]
        except Exception as e:
            self.logger.error(f"Error detecting conversation end: {str(e)}")
            return False

    async def save_evaluation_log(self, evaluation_data: Dict[str, Any]) -> None:
        """Save evaluation data to logs following EvaluationStorage pattern."""
        try:
            # Create comprehensive evaluation record
            agent_evaluations = {
                agent.name: evaluation_data.get("agent_evaluations", {}).get(agent.name, {})
                for agent in self.group_chat.agents
            }
            
            # Store evaluation using EvaluationStorage pattern
            self.evaluation_storage.store_evaluation(
                conversation_id=str(id(self)),
                evaluation_data=evaluation_data,
                agent_evaluations=agent_evaluations
            )
            
        except Exception as e:
            self.logger.error(f"Error saving evaluation log: {str(e)}")
            raise DataProcessingError(f"Failed to store evaluation: {str(e)}")

    async def send_evaluation_summary(self, evaluation_data: Dict[str, Any]) -> None:
        """Send evaluation summary following ConversationEvaluator pattern."""
        try:
            # Get historical comparison
            historical_comparison = self.evaluator.compare_with_historical_metrics(
                evaluation_data.get("metrics", {})
            )
            
            # Create evaluation record
            evaluation_record = self._create_evaluation_record(
                evaluation_data=evaluation_data,
                historical_comparison=historical_comparison
            )
            
            # Format and log summary
            summary = self._format_evaluation_summary(evaluation_record)
            self.logger.info(f"Evaluation summary generated:\n{summary}")
            
            # Generate and add recommendations
            recommendations = self._generate_recommendations(evaluation_data)
            
            # Send email notification
            await self._send_email_notification(
                summary=summary,
                recommendations=recommendations,
                evaluation_data=evaluation_data
            )
            
        except Exception as e:
            self.logger.error(f"Error sending evaluation summary: {str(e)}")

    def _create_evaluation_record(self, evaluation_data: Dict[str, Any],
                                historical_comparison: Dict[str, Any]) -> Dict[str, Any]:
        """Create evaluation record following EvaluationStorage pattern."""
        return {
            "id": str(id(self)),
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "conversation": evaluation_data.get("metrics", {}),
                "flow": evaluation_data.get("flow_metrics", {}),
                "timing": evaluation_data.get("timing_metrics", {}),
                "historical_comparison": historical_comparison
            },
            "analysis": {
                "strengths": evaluation_data.get("strengths", []),
                "areas_for_improvement": evaluation_data.get("areas_for_improvement", []),
                "action_items": evaluation_data.get("action_items", [])
            },
            "flags": {
                "requires_review": evaluation_data.get("requires_review", False),
                "high_priority": evaluation_data.get("high_priority", False),
                "has_errors": bool(evaluation_data.get("error_metrics"))
            }
        }

    def _format_evaluation_summary(self, evaluation_record: Dict[str, Any]) -> str:
        """Format evaluation summary following RepresentativeAgent pattern."""
        try:
            metrics = evaluation_record["metrics"]
            analysis = evaluation_record["analysis"]
            historical = metrics.get("historical_comparison", {})
            
            summary_parts = [
                "Conversation Evaluation Summary",
                f"\nTimestamp: {datetime.now().isoformat()}",
                "\nOverall Metrics:",
                *[f"- {k}: {v}/10" for k, v in metrics["conversation"].items()],
                "\nFlow Metrics:",
                *[f"- {k}: {v}/10" for k, v in metrics["flow"].items()],
                "\nOutcome Metrics:",
                *[f"- {k}: {v}/10" if isinstance(v, (int, float)) else f"- {k}: {v}"
                  for k, v in metrics.get("outcome_metrics", {}).items()],
                "\nHistorical Comparison:",
                *[f"- {k}: {v['percent_change']:+.1f}%" 
                  for k, v in historical.get("current_vs_average", {}).items()],
                "\nStrengths:",
                *[f"- {s}" for s in analysis["strengths"]],
                "\nAreas for Improvement:",
                *[f"- {a}" for a in analysis["areas_for_improvement"]],
                "\nAction Items:",
                *[f"- {item}" for item in analysis.get("action_items", [])]
            ]
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            self.logger.error(f"Error formatting evaluation summary: {str(e)}")
            return "Error generating evaluation summary"

    def _generate_recommendations(self, evaluation_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate improvement recommendations based on metrics."""
        try:
            recommendations = {
                "Agent Performance": [],
                "Conversation Flow": [],
                "User Experience": [],
                "Team Collaboration": []
            }
            
            metrics = evaluation_data.get("metrics", {}).get("conversation", {})
            flow_metrics = evaluation_data.get("flow_metrics", {})
            outcome_metrics = evaluation_data.get("outcome_metrics", {})
            
            # Check flow metrics following DailyFeedbackGenerator pattern
            if flow_metrics.get("conversation_coherence", 0) < 7:
                recommendations["Conversation Flow"].append(
                    "Improve conversation flow and natural progression"
                )
            if flow_metrics.get("context_retention", 0) < 7:
                recommendations["Conversation Flow"].append(
                    "Enhance context maintenance throughout conversations"
                )
            if flow_metrics.get("handoff_smoothness", 0) < 7:
                recommendations["Team Collaboration"].append(
                    "Optimize agent handoffs and transitions"
                )
                
            # Check efficiency metrics
            if metrics.get("time_efficiency", 0) < 7:
                recommendations["Agent Performance"].append(
                    "Work on reducing resolution time"
                )
            if metrics.get("resource_utilization", 0) < 7:
                recommendations["Team Collaboration"].append(
                    "Optimize agent resource allocation"
                )
                
            # Check outcome metrics
            if outcome_metrics.get("resolution_completeness", 0) < 7:
                recommendations["User Experience"].append(
                    "Focus on improving issue resolution completeness"
                )
            if outcome_metrics.get("user_satisfaction", 0) < 7:
                recommendations["User Experience"].append(
                    "Focus on improving user satisfaction"
                )
            if outcome_metrics.get("follow_up_needed", False):
                recommendations["Agent Performance"].append(
                    "Reduce cases requiring follow-up"
                )
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {str(e)}")
            return {}

    async def handle_conversation_end(self) -> str:
        """Handle end of conversation tasks."""
        try:
            # Extract action items
            await self._extract_action_items()
            
            # Generate final evaluation
            evaluation_data = await self.evaluate_conversation()
            
            # Save conversation record
            await self.save_conversation_record()
            
            # Generate user satisfaction survey
            survey_link = await self.generate_satisfaction_survey()
            
            return f"Thank you for your time. {survey_link}"
        except Exception as e:
            self.logger.error(f"Error handling conversation end: {str(e)}")
            return "Thank you for your time."

    async def _extract_action_items(self) -> List[str]:
        """Extract action items from conversation history."""
        try:
            messages = [{
                "role": "system",
                "content": """Review the conversation and extract action items.
                Return as JSON array of strings, each representing a specific action item."""
            },
            {"role": "user", "content": str(self.conversation_history)}]
            
            response = await self.openai_service.get_completion(messages)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error extracting action items: {str(e)}")
            return []

    async def save_conversation_record(self) -> None:
        """Save the complete conversation record."""
        try:
            record = {
                "id": str(id(self)),
                "timestamp": datetime.now().isoformat(),
                "conversation_history": self.conversation_history,
                "metrics": await self.evaluate_conversation(),
                "agents": [agent.name for agent in self.group_chat.agents]
            }
            
            file_manager = FileManager()
            file_manager.save_conversation(str(id(self)), record)
        except Exception as e:
            self.logger.error(f"Error saving conversation record: {str(e)}")

    async def generate_satisfaction_survey(self) -> str:
        """Generate a satisfaction survey link."""
        try:
            survey_id = f"survey_{str(id(self))}"
            return f"Please take a moment to complete our satisfaction survey: https://example.com/survey/{survey_id}"
        except Exception as e:
            self.logger.error(f"Error generating survey link: {str(e)}")
            return ""

    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Handle errors with enhanced recovery mechanisms."""
        try:
            result, message = await self.error_handler.handle_error(error, context)
            if result:
                self.logger.info(f"Successfully recovered from error: {message}")
                return True
                
            self.logger.error(f"Failed to recover from error: {message}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error in error recovery: {str(e)}")
            return False
            
    async def save_conversation_state(self) -> None:
        """Save conversation state for recovery."""
        try:
            state = {
                "messages": self.conversation_history,
                "metrics": await self._evaluate_detailed_metrics(),
                "timestamp": datetime.now().isoformat()
            }
            
            self.recovery_states[len(self.conversation_history)] = state
            
        except Exception as e:
            self.logger.error(f"Error saving conversation state: {str(e)}")

    async def process_message(self, message: str) -> str:
        """Process a message with enhanced error handling."""
        try:
            # Save current state before processing
            await self._save_state()
            
            # Process message with timeout
            response = await self._process_with_timeout({
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update conversation history
            self.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })
            
            self.conversation_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
            return response
            
        except Exception as e:
            # Attempt error recovery
            context = {
                "message": message,
                "messages": self.conversation_history,
                "error": str(e)
            }
            
            if await self.handle_error(e, context):
                # Retry after successful recovery
                return await self.process_message(message)
                
            # Fallback response
            return "I apologize, but I'm having trouble processing your request. Please try again."

    async def _process_with_timeout(self, context: Dict[str, Any]) -> str:
        """Process message with timeout handling."""
        try:
            async with asyncio.timeout(self.config.DEFAULT_CONFIG["timeout"]):
                return await self.group_chat.process_message(
                    message=context["message"],
                    sender=self.group_chat.agents[0]
                )
        except asyncio.TimeoutError:
            raise TimeoutError("Message processing timed out")

    async def _save_state(self) -> None:
        """Save current conversation state."""
        try:
            state = {
                "messages": self.conversation_history.copy(),
                "timestamp": datetime.now().isoformat()
            }
            
            self.recovery_states[len(self.conversation_history)] = state
            
            # Keep only last 5 states
            if len(self.recovery_states) > 5:
                oldest_key = min(self.recovery_states.keys())
                del self.recovery_states[oldest_key]
                
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")

    async def _get_recovery_strategy(self, error_type: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get appropriate recovery strategy based on error type."""
        strategies = {
            "JSONDecodeError": {
                "method": self.recovery_strategy.retry_with_format_correction,
                "max_attempts": 3
            },
            "TimeoutError": {
                "method": self.recovery_strategy.handle_timeout,
                "max_attempts": 3
            },
            "StateError": {
                "method": self.recovery_strategy.restore_conversation_state,
                "max_attempts": 1
            }
        }
        
        return strategies.get(error_type)
        
    async def _execute_recovery_strategy(self, 
                                      strategy: Dict[str, Any], 
                                      context: Dict[str, Any]) -> bool:
        """Execute selected recovery strategy."""
        try:
            method = strategy["method"]
            max_attempts = strategy["max_attempts"]
            
            for attempt in range(max_attempts):
                if await method(context):
                    return True
                    
                await asyncio.sleep(1 * (2 ** attempt))
                
            return False
            
        except Exception as e:
            self.logger.error(f"Recovery strategy execution failed: {str(e)}")
            return False

    async def _collect_error_context(self, error: Exception, message: str) -> Dict[str, Any]:
        """Collect comprehensive error context for recovery."""
        try:
            return {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "conversation_state": {
                    "history_length": len(self.conversation_history),
                    "last_message": self.conversation_history[-1] if self.conversation_history else None,
                    "active_agents": [agent.name for agent in self.group_chat.agents]
                },
                "metrics": await self._evaluate_detailed_metrics(),
                "recovery_states": list(self.recovery_states.keys())
            }
        except Exception as e:
            self.logger.error(f"Error collecting context: {str(e)}")
            return {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": datetime.now().isoformat()
            }

    async def _send_email_notification(self, 
                                        summary: str,
                                        recommendations: Dict[str, List[str]],
                                        evaluation_data: Dict[str, Any]) -> None:
        """Send email notification with evaluation summary and recommendations."""
        try:
            # Format email content
            email_content = [
                "<h2>Conversation Evaluation Summary</h2>",
                "<div style='margin: 20px 0;'>",
                summary.replace("\n", "<br>"),
                "</div>"
            ]
            
            # Add critical alerts section if needed
            flags = evaluation_data.get("flags", {})
            if any(flags.values()):
                email_content.extend([
                    "<h2 style='color: #d32f2f;'>⚠️ Critical Alerts</h2>",
                    "<ul style='color: #d32f2f;'>",
                    *[f"<li>{flag.replace('_', ' ').title()}</li>" 
                      for flag, value in flags.items() if value],
                    "</ul>"
                ])
            
            # Add recommendations section
            if any(recommendations.values()):
                email_content.extend([
                    "<h2>Recommendations</h2>",
                    "<div style='margin: 20px 0;'>"
                ])
                
                for category, items in recommendations.items():
                    if items:
                        email_content.extend([
                            f"<h3>{category}</h3>",
                            "<ul>",
                            *[f"<li>{item}</li>" for item in items],
                            "</ul>"
                        ])
                
                email_content.append("</div>")
            
            # Add performance metrics
            metrics = evaluation_data.get("metrics", {})
            if metrics:
                email_content.extend([
                    "<h2>Performance Metrics</h2>",
                    "<table style='width: 100%; border-collapse: collapse;'>",
                    "<tr><th style='text-align: left; padding: 8px;'>Metric</th><th style='text-align: right; padding: 8px;'>Score</th></tr>"
                ])
                
                # Add conversation metrics
                for k, v in metrics.get("conversation", {}).items():
                    if isinstance(v, (int, float)):
                        color = "#4caf50" if v >= 7 else "#ff9800" if v >= 5 else "#f44336"
                        email_content.append(
                            f"<tr><td style='padding: 8px;'>{k.replace('_', ' ').title()}</td>"
                            f"<td style='text-align: right; color: {color}; padding: 8px;'>{v}/10</td></tr>"
                        )
                
                # Add flow metrics
                for k, v in metrics.get("flow", {}).items():
                    if isinstance(v, (int, float)):
                        color = "#4caf50" if v >= 7 else "#ff9800" if v >= 5 else "#f44336"
                        email_content.append(
                            f"<tr><td style='padding: 8px;'>{k.replace('_', ' ').title()}</td>"
                            f"<td style='text-align: right; color: {color}; padding: 8px;'>{v}/10</td></tr>"
                        )
                
                email_content.append("</table>")
            
            # Add agent evaluations
            agent_evaluations = evaluation_data.get("agent_evaluations", {})
            if agent_evaluations:
                email_content.extend([
                    "<h2>Agent Performance</h2>",
                    "<div style='margin: 20px 0;'>"
                ])
                
                for agent, metrics in agent_evaluations.items():
                    email_content.extend([
                        f"<h3>{agent}</h3>",
                        "<table style='width: 100%; border-collapse: collapse; margin-bottom: 20px;'>"
                    ])
                    
                    for category, scores in metrics.items():
                        email_content.append(
                            f"<tr><td colspan='2' style='padding: 8px; background-color: #f5f5f5;'>"
                            f"<strong>{category.replace('_', ' ').title()}</strong></td></tr>"
                        )
                        
                        for metric, score in scores.items():
                            color = "#4caf50" if score >= 7 else "#ff9800" if score >= 5 else "#f44336"
                            email_content.append(
                                f"<tr><td style='padding: 8px;'>{metric}</td>"
                                f"<td style='text-align: right; color: {color}; padding: 8px;'>{score}/10</td></tr>"
                            )
                    
                    email_content.append("</table>")
                
                email_content.append("</div>")
            
            # Add timing metrics
            timing_metrics = metrics.get("timing", {})
            if timing_metrics:
                email_content.extend([
                    "<h2>Timing Analysis</h2>",
                    "<table style='width: 100%; border-collapse: collapse;'>",
                    "<tr><th style='text-align: left; padding: 8px;'>Metric</th><th style='text-align: right; padding: 8px;'>Value</th></tr>",
                    f"<tr><td style='padding: 8px;'>Average Response Time</td><td style='text-align: right; padding: 8px;'>{timing_metrics.get('avg_response_time', 0):.1f}s</td></tr>",
                    f"<tr><td style='padding: 8px;'>Total Duration</td><td style='text-align: right; padding: 8px;'>{timing_metrics.get('total_duration', 0):.1f}m</td></tr>",
                    "</table>"
                ])
            
            # Add historical comparison
            historical = metrics.get("historical_comparison", {})
            if historical.get("current_vs_average"):
                email_content.extend([
                    "<h2>Historical Performance</h2>",
                    "<table style='width: 100%; border-collapse: collapse;'>",
                    "<tr><th style='text-align: left; padding: 8px;'>Metric</th><th style='text-align: right; padding: 8px;'>Change</th></tr>"
                ])
                
                for k, v in historical["current_vs_average"].items():
                    change = v['percent_change']
                    color = "#4caf50" if change > 0 else "#f44336" if change < 0 else "#757575"
                    email_content.extend([
                        f"<tr><td style='padding: 8px;'>{k.replace('_', ' ').title()}</td>"
                        f"<td style='text-align: right; color: {color}; padding: 8px;'>{change:+.1f}%</td></tr>"
                    ])
                
                email_content.append("</table>")
            
            # Add footer
            email_content.extend([
                "<hr style='margin: 30px 0;'>",
                "<p style='color: #757575; font-size: 12px;'>",
                f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "<br>This is an automated evaluation summary. Please do not reply to this email.",
                "</p>"
            ])
            
            # Send email using EmailService
            subject = "Conversation Evaluation Summary"
            if any(flags.values()):
                subject = "🚨 " + subject + " - Attention Required"
            
            await self.email_service.send_email(
                subject=f"{subject} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                recipients=self.config.get_notification_recipients(),
                html_content="\n".join(email_content),
                priority="high" if any(flags.values()) else "normal"
            )
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {str(e)}")
            # Don't raise exception to avoid disrupting the main workflow
