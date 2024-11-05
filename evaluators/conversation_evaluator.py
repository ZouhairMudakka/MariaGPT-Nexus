from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import os
from agents.evaluation_metrics import MetricsValidator, EvaluationStorage, ErrorMetrics
from agents.utils.logger import AgentLogger

class ConversationEvaluator:
    def __init__(self, log_dir: str = "evaluation_logs"):
        self.log_dir = log_dir
        self.validator = MetricsValidator()
        self.logger = AgentLogger("ConversationEvaluator")
        self.storage = EvaluationStorage()
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
                    conversation_id,
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
            self.logger.logger.error(f"Evaluation error: {str(e)}")
            return self._get_fallback_metrics(), error_metrics

    def _get_fallback_metrics(self):
        return self.evaluate_agent("", "", [], [])[0] 