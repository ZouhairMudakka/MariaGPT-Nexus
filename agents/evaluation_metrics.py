from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os
from enum import Enum
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvaluationError(Exception):
    """Base exception for evaluation errors"""
    pass

class MetricsValidationError(EvaluationError):
    """Raised when metrics validation fails"""
    pass

class DataProcessingError(EvaluationError):
    """Raised when data processing fails"""
    pass

@dataclass
class TimingMetrics:
    first_response_time: float   # Time to first response in seconds
    avg_response_time: float     # Average response time in seconds
    total_interaction_time: float # Total time agent spent in conversation
    think_time: float           # Time spent processing before responses
    handoff_time: float         # Time spent in transitions

@dataclass
class AgentMetrics:
    # Core metrics
    response_quality: float      # 0-10: Accuracy, relevance, and clarity
    task_completion: float       # 0-10: How well agent completed their assigned tasks
    knowledge_application: float # 0-10: Effective use of domain knowledge
    
    # Interaction metrics
    timing: TimingMetrics       # Detailed timing metrics
    context_awareness: float    # 0-10: Understanding of conversation context
    initiative: float          # 0-10: Proactive problem identification/resolution
    
    # Role-specific metrics
    role_effectiveness: float   # 0-10: Effectiveness in assigned role
    domain_expertise: float     # 0-10: Demonstrated expertise in domain
    
    # Collaboration metrics
    handoff_quality: float      # 0-10: Quality of transitions
    team_coordination: float    # 0-10: Coordination with other agents
    
    # Error handling
    error_count: int           # Number of mistakes or misunderstandings
    recovery_effectiveness: float # 0-10: How well errors were handled
    
    def calculate_overall_score(self) -> float:
        weights = {
            'response_quality': 0.2,
            'task_completion': 0.2,
            'knowledge_application': 0.15,
            'context_awareness': 0.1,
            'initiative': 0.1,
            'role_effectiveness': 0.1,
            'handoff_quality': 0.15
        }
        
        score = sum(getattr(self, metric) * weight 
                   for metric, weight in weights.items())
        return round(score, 2)

@dataclass
class ConversationMetrics:
    # Flow metrics
    flow_quality: float         # 0-10: Natural conversation progression
    context_consistency: float  # 0-10: Maintenance of context
    topic_coverage: float      # 0-10: Completeness of topic coverage
    
    # Efficiency metrics
    time_efficiency: float      # 0-10: Overall time to resolution
    interaction_efficiency: float # 0-10: Efficiency of interactions
    resource_utilization: float # 0-10: Effective use of agent resources
    
    # Outcome metrics
    goal_achievement: float     # 0-10: Achievement of user's objectives
    issue_resolution: float     # 0-10: Completeness of problem resolution
    user_satisfaction: float    # 0-10: Estimated user satisfaction
    
    # Collaboration metrics
    handoff_smoothness: float   # 0-10: Quality of agent transitions
    team_synergy: float        # 0-10: Effectiveness of agent collaboration
    
    def calculate_overall_score(self) -> float:
        weights = {
            'flow_quality': 0.15,
            'goal_achievement': 0.2,
            'issue_resolution': 0.2,
            'user_satisfaction': 0.25,
            'handoff_smoothness': 0.1,
            'team_synergy': 0.1
        }
        
        score = sum(getattr(self, metric) * weight 
                   for metric, weight in weights.items())
        return round(score, 2)

@dataclass
class UserFeedback:
    # Explicit feedback
    rating: Optional[float]     # User-provided rating (0-10)
    comments: Optional[str]     # User's explicit comments
    
    # Sentiment analysis
    sentiment_score: float      # Overall sentiment (-1 to 1)
    sentiment_progression: List[float]  # Sentiment changes over time
    
    # Interaction patterns
    engagement_level: float     # 0-10: User engagement in conversation
    cooperation_level: float    # 0-10: User cooperation with agents
    frustration_indicators: List[str]  # Signs of user frustration
    satisfaction_signals: List[str]    # Signs of user satisfaction
    
    # Issue resolution
    needs_met: float           # 0-10: How well needs were addressed
    pain_points: List[str]     # Identified user frustrations
    unresolved_issues: List[str] # Outstanding issues
    
@dataclass
class ErrorMetrics:
    timestamp: str
    error_type: str
    error_message: str
    severity: str
    recovery_action: str
    affected_metrics: List[str]

class MetricsValidator:
    def validate_metrics_dict(self, metrics: Dict[str, Any]) -> None:
        """Validate all metrics in a dictionary"""
        try:
            for category, values in metrics.items():
                if isinstance(values, dict):
                    self.validate_metrics_dict(values)
                elif isinstance(values, (int, float)):
                    self.validate_score(values, category)
        except Exception as e:
            raise MetricsValidationError(f"Metrics validation failed: {str(e)}")
    
    def validate_timing_metrics(self, timing_metrics: TimingMetrics) -> None:
        """Validate timing metrics dataclass"""
        for field, value in timing_metrics.__dict__.items():
            self.validate_timing(value, field)

    @staticmethod
    def validate_score(score: float, metric_name: str) -> float:
        """Validate score is within acceptable range"""
        try:
            score = float(score)
            if metric_name == "sentiment_score":
                if not -1 <= score <= 1:
                    raise MetricsValidationError(f"Sentiment score {score} out of range [-1, 1]")
            else:
                if not 0 <= score <= 10:
                    raise MetricsValidationError(f"Score {score} out of range [0, 10]")
            return score
        except ValueError:
            raise MetricsValidationError(f"Invalid score value: {score}")

    @staticmethod
    def validate_timing(timing: float, metric_name: str) -> float:
        """Validate timing metrics"""
        try:
            timing = float(timing)
            if timing < 0:
                raise MetricsValidationError(f"Negative timing value for {metric_name}: {timing}")
            return timing
        except ValueError:
            raise MetricsValidationError(f"Invalid timing value: {timing}")

class MetricsLogger:
    def __init__(self, log_dir: str = "evaluation_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.error_log = self.log_dir / "error_log.json"

    def log_error(self, error: ErrorMetrics) -> None:
        """Log evaluation errors"""
        try:
            errors = []
            if self.error_log.exists():
                with open(self.error_log, 'r') as f:
                    errors = json.load(f)
            
            errors.append(vars(error))
            
            with open(self.error_log, 'w') as f:
                json.dump(errors, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to log error: {str(e)}")

class EvaluationStorage:
    def __init__(self):
        # Define base paths
        self.base_path = Path("data/agent_evaluations")
        self.metrics_path = self.base_path / "metrics"
        self.logs_path = self.base_path / "logs"
        
        # Create directory structure
        for path in [self.base_path, self.metrics_path, self.logs_path]:
            path.mkdir(parents=True, exist_ok=True)
            
        # Define specific files
        self.performance_file = self.metrics_path / "agent_performance_metrics.json"
        self.flow_metrics_file = self.metrics_path / "conversation_flow_metrics.json"
        
        self._initialize_storage()

    def _initialize_storage(self):
        if not self.performance_file.exists():
            self._save_evaluations(self.performance_file, {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                    "description": "Comprehensive agent and conversation evaluations"
                },
                "conversations": {
                    "completed": [],
                    "ongoing": [],
                    "flagged_for_review": []
                },
                "agents": {
                    "performance_history": {},
                    "aggregate_metrics": {}
                }
            })
        
        if not self.flow_metrics_file.exists():
            self._save_evaluations(self.flow_metrics_file, {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                    "description": "Conversation flow and interaction metrics"
                },
                "flow_metrics": [],
                "interaction_patterns": [],
                "handoff_analytics": []
            })

    def _load_evaluations(self, file: Path) -> Dict[str, Any]:
        try:
            with open(file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading evaluations: {str(e)}")
            return {"conversations": [], "agents": {}, "metrics_history": []}

    def _save_evaluations(self, file: Path, data: Dict[str, Any]) -> None:
        try:
            with open(file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving evaluations: {str(e)}")

    def store_evaluation(self, conversation_id: str, evaluation_data: Dict[str, Any], 
                        agent_evaluations: Dict[str, Any]) -> None:
        """Store new evaluation data with flow metrics"""
        try:
            # Load current data from both files
            performance_data = self._load_evaluations(self.performance_file)
            flow_data = self._load_evaluations(self.flow_metrics_file)
            
            # Create flow metrics record
            flow_metrics = self._create_flow_metrics(conversation_id, evaluation_data)
            
            # Update flow metrics file
            flow_data["flow_metrics"].append(flow_metrics)
            flow_data["interaction_patterns"].append(flow_metrics["interaction_pattern"])
            flow_data["handoff_analytics"].append({
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
                "handoff_metrics": flow_metrics["flow_metrics"]["handoff_smoothness"],
                "context_retention": flow_metrics["flow_metrics"]["context_retention"]
            })
            flow_data["metadata"]["last_updated"] = datetime.now().isoformat()
            
            # Create and store performance record
            evaluation_record = self._create_evaluation_record(
                conversation_id, evaluation_data, agent_evaluations, flow_metrics)
            
            # Update performance metrics file
            self._update_performance_data(performance_data, evaluation_record, agent_evaluations)
            
            # Save both files
            self._save_evaluations(self.performance_file, performance_data)
            self._save_evaluations(self.flow_metrics_file, flow_data)
            
        except Exception as e:
            logger.error(f"Error storing evaluation: {str(e)}")
            raise DataProcessingError(f"Failed to store evaluation: {str(e)}")

    def _create_flow_metrics(self, conversation_id: str, 
                           evaluation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create flow metrics record"""
        return {
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "flow_metrics": {
                "coherence": evaluation_data.get("flow_metrics", {}).get("conversation_coherence", 0),
                "context_retention": evaluation_data.get("flow_metrics", {}).get("context_retention", 0),
                "handoff_smoothness": evaluation_data.get("flow_metrics", {}).get("handoff_smoothness", 0),
                "goal_progression": evaluation_data.get("flow_metrics", {}).get("goal_progression", 0)
            },
            "timing_metrics": evaluation_data.get("timing_metrics", {}),
            "interaction_pattern": {
                "agent_switches": evaluation_data.get("agent_switches", 0),
                "topic_transitions": evaluation_data.get("topic_transitions", 0),
                "context_switches": evaluation_data.get("context_switches", 0)
            }
        }

    def _update_performance_data(self, performance_data: Dict[str, Any], 
                               evaluation_record: Dict[str, Any],
                               agent_evaluations: Dict[str, Any]) -> None:
        """Update performance data with new evaluation"""
        # Update conversations
        if evaluation_record["flags"]["requires_review"]:
            performance_data["conversations"]["flagged_for_review"].append(evaluation_record)
        else:
            performance_data["conversations"]["completed"].append(evaluation_record)
        
        # Update agent performance history
        for agent_name, metrics in agent_evaluations.items():
            if agent_name not in performance_data["agents"]["performance_history"]:
                performance_data["agents"]["performance_history"][agent_name] = []
            
            performance_data["agents"]["performance_history"][agent_name].append({
                "conversation_id": evaluation_record["id"],
                "timestamp": evaluation_record["metadata"]["timestamp"],
                "metrics": metrics
            })
        
        performance_data["metadata"]["last_updated"] = datetime.now().isoformat()

    def _create_evaluation_record(self, conversation_id: str, evaluation_data: Dict[str, Any],
                                agent_evaluations: Dict[str, Any], flow_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive evaluation record"""
        return {
            "id": conversation_id,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "duration": evaluation_data.get("duration"),
                "category": evaluation_data.get("category", "general"),
                "tags": evaluation_data.get("tags", [])
            },
            "metrics": {
                "conversation": evaluation_data.get("metrics", {}),
                "flow": flow_metrics["flow_metrics"],
                "agents": agent_evaluations,
                "user_satisfaction": evaluation_data.get("user_satisfaction", {})
            },
            "analysis": {
                "summary": evaluation_data.get("summary", ""),
                "strengths": evaluation_data.get("strengths", []),
                "areas_for_improvement": evaluation_data.get("areas_for_improvement", []),
                "action_items": evaluation_data.get("action_items", [])
            },
            "flags": {
                "requires_review": evaluation_data.get("requires_review", False),
                "high_priority": evaluation_data.get("high_priority", False),
                "has_errors": evaluation_data.get("has_errors", False)
            }
        }

class DailyFeedbackGenerator:
    def __init__(self):
        pass
    # Add methods as needed

class ConversationEvaluator:
    def __init__(self, log_dir: str = "evaluation_logs"):
        self.log_dir = log_dir
        self.validator = MetricsValidator()
        self.logger = MetricsLogger(log_dir)
        self.storage = EvaluationStorage()
        self.feedback_generator = DailyFeedbackGenerator(
            evaluations_path=os.path.join(log_dir, "agent_evaluations")
        )
        os.makedirs(log_dir, exist_ok=True)

    def evaluate_agent(self, 
                      agent_name: str,
                      conversation_id: str,
                      conversation_history: List[Dict[str, Any]],
                      agent_interactions: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Optional[ErrorMetrics]]:
        try:
            evaluation_result = self._evaluate_agent_metrics(
                agent_name, conversation_history, agent_interactions)
            
            if evaluation_result:
                self.storage.store_evaluation(
                    conversation_id=conversation_id,
                    evaluation_data=evaluation_result,
                    agent_evaluations={agent_name: evaluation_result}
                )
            
            return evaluation_result, None
            
        except Exception as e:
            error_metrics = ErrorMetrics(
                timestamp=datetime.now().isoformat(),
                error_type="EvaluationError",
                error_message=str(e),
                severity="high",
                recovery_action="Using fallback metrics",
                affected_metrics=["all"]
            )
            self.logger.log_error(error_metrics)
            return self._get_fallback_metrics(), error_metrics

    def _evaluate_agent_metrics(self,
                          agent_name: str,
                          conversation_history: List[Dict[str, Any]],
                          agent_interactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate agent performance metrics"""
        try:
            # Extract agent-specific interactions
            agent_messages = [
                msg for msg in conversation_history 
                if msg.get("role") == "assistant" and msg.get("agent") == agent_name
            ]
            
            # Calculate timing metrics
            timing_metrics = TimingMetrics(
                first_response_time=self._calculate_first_response_time(agent_interactions),
                avg_response_time=self._calculate_avg_response_time(agent_interactions),
                total_interaction_time=self._calculate_total_time(agent_interactions),
                think_time=self._calculate_think_time(agent_interactions),
                handoff_time=self._calculate_handoff_time(agent_interactions)
            )
            
            # Calculate agent metrics
            metrics = AgentMetrics(
                response_quality=self._evaluate_response_quality(agent_messages),
                task_completion=self._evaluate_task_completion(agent_interactions),
                knowledge_application=self._evaluate_knowledge_application(agent_messages),
                timing=timing_metrics,
                context_awareness=self._evaluate_context_awareness(agent_messages),
                initiative=self._evaluate_initiative(agent_messages),
                role_effectiveness=self._evaluate_role_effectiveness(agent_name, agent_messages),
                domain_expertise=self._evaluate_domain_expertise(agent_messages),
                handoff_quality=self._evaluate_handoff_quality(agent_interactions),
                team_coordination=self._evaluate_team_coordination(agent_interactions),
                error_count=self._count_errors(agent_messages),
                recovery_effectiveness=self._evaluate_recovery_effectiveness(agent_messages)
            )
            
            return {
                "agent_name": agent_name,
                "metrics": metrics.__dict__,
                "overall_score": metrics.calculate_overall_score(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error evaluating agent metrics: {str(e)}")
            return self._get_fallback_metrics()

    def _validate_metrics(self, metrics: Dict[str, Any]) -> None:
        """Validate all metrics in evaluation result"""
        try:
            for category, values in metrics.items():
                if isinstance(values, dict):
                    for metric, score in values.items():
                        if isinstance(score, (int, float)):
                            self.validator.validate_score(score, metric)
                elif isinstance(values, (int, float)):
                    self.validator.validate_score(values, category)
        except Exception as e:
            raise MetricsValidationError(f"Metrics validation failed: {str(e)}")

    def _get_fallback_metrics(self) -> Dict[str, Any]:
        """Return safe fallback metrics when evaluation fails"""
        return {
            "response_metrics": {
                "accuracy": 5,
                "relevance": 5,
                "clarity": 5,
                "completeness": 5
            },
            "interaction_metrics": {
                "empathy": 5,
                "professionalism": 5,
                "proactiveness": 5,
                "adaptability": 5
            },
            "error_flag": True,
            "requires_review": True
        }

    def compare_with_historical_metrics(self, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current conversation metrics with historical averages."""
        try:
            historical_data = self.load_historical_metrics()
            
            comparison = {
                "current_vs_average": {},
                "trends": {},
                "improvements": [],
                "degradations": []
            }
            
            for metric, value in current_metrics.items():
                if metric in historical_data["averages"]:
                    diff = value - historical_data["averages"][metric]
                    comparison["current_vs_average"][metric] = {
                        "current": value,
                        "average": historical_data["averages"][metric],
                        "difference": diff,
                        "percent_change": (diff / historical_data["averages"][metric]) * 100
                    }
                    
                    if diff > 0:
                        comparison["improvements"].append(metric)
                    elif diff < 0:
                        comparison["degradations"].append(metric)
                        
            return comparison
        except Exception as e:
            self.logger.error(f"Error in comparative analysis: {str(e)}")
            return {}

    def load_historical_metrics(self) -> Dict[str, Any]:
        """Load historical metrics for comparison"""
        try:
            performance_data = self.storage._load_evaluations(self.storage.performance_file)
            
            # Calculate averages from completed conversations
            metrics_sum = {}
            metrics_count = {}
            
            for conv in performance_data["conversations"]["completed"]:
                for metric, value in conv["metrics"]["conversation"].items():
                    if isinstance(value, (int, float)):
                        metrics_sum[metric] = metrics_sum.get(metric, 0) + value
                        metrics_count[metric] = metrics_count.get(metric, 0) + 1
            
            averages = {
                metric: metrics_sum[metric] / count 
                for metric, count in metrics_count.items()
            }
            
            return {"averages": averages}
        except Exception as e:
            logger.error(f"Error loading historical metrics: {str(e)}")
            return {"averages": {}}

    def _calculate_first_response_time(self, interactions: List[Dict[str, Any]]) -> float:
        """Calculate time to first response"""
        try:
            if not interactions:
                return 0.0
            first_interaction = interactions[0]
            return self.validator.validate_timing(
                first_interaction.get("response_time", 0), 
                "first_response_time"
            )
        except Exception as e:
            logger.error(f"Error calculating first response time: {str(e)}")
            return 0.0

    def _calculate_avg_response_time(self, interactions: List[Dict[str, Any]]) -> float:
        """Calculate average response time"""
        try:
            if not interactions:
                return 0.0
            response_times = [
                interaction.get("response_time", 0) 
                for interaction in interactions
            ]
            avg_time = sum(response_times) / len(response_times)
            return self.validator.validate_timing(avg_time, "avg_response_time")
        except Exception as e:
            logger.error(f"Error calculating average response time: {str(e)}")
            return 0.0

    def evaluate_conversation_flow(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate overall conversation flow metrics"""
        try:
            flow_metrics = self._calculate_flow_metrics(conversation_history)
            timing_metrics = self._calculate_timing_metrics(conversation_history)
            outcome_metrics = self._calculate_outcome_metrics(conversation_history)
            
            metrics = {
                "flow_metrics": flow_metrics,
                "timing_metrics": timing_metrics,
                "outcome_metrics": outcome_metrics,
                "interaction_pattern": self._analyze_interaction_pattern(conversation_history)
            }
            
            self.validator.validate_metrics_dict(metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating conversation flow: {str(e)}")
            return self._get_fallback_metrics()