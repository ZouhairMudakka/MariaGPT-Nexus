from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
from ...utils.logger import Logger, MetricsLogger
from collections import defaultdict

class PerformanceMonitor:
    def __init__(self, logger: Logger, metrics_logger: MetricsLogger):
        self.logger = logger
        self.metrics_logger = metrics_logger
        self.performance_metrics: Dict[str, List[Dict[str, Any]]] = {}
        self.alerts: List[Dict[str, Any]] = []
        
    async def track_metric(self, 
                         agent_id: str, 
                         metric_type: str, 
                         value: Any,
                         metadata: Optional[Dict[str, Any]] = None) -> None:
        """Track a performance metric."""
        try:
            metric = {
                "timestamp": datetime.now().isoformat(),
                "type": metric_type,
                "value": value,
                "metadata": metadata or {}
            }
            
            if agent_id not in self.performance_metrics:
                self.performance_metrics[agent_id] = []
            
            self.performance_metrics[agent_id].append(metric)
            await self._check_thresholds(agent_id, metric)
            await self.metrics_logger.log_metric(agent_id, metric)
            
        except Exception as e:
            self.logger.error(f"Error tracking metric: {str(e)}")
            
    async def _check_thresholds(self, agent_id: str, metric: Dict[str, Any]) -> None:
        """Check if metric exceeds defined thresholds."""
        thresholds = {
            "response_time": 5.0,  # seconds
            "error_rate": 0.1,     # 10%
            "memory_usage": 0.8    # 80%
        }
        
        if metric["type"] in thresholds:
            threshold = thresholds[metric["type"]]
            if isinstance(metric["value"], (int, float)) and metric["value"] > threshold:
                await self._create_alert(agent_id, metric, threshold)
                
    async def _create_alert(self, 
                          agent_id: str, 
                          metric: Dict[str, Any], 
                          threshold: float) -> None:
        """Create and log performance alert."""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "metric_type": metric["type"],
            "value": metric["value"],
            "threshold": threshold,
            "severity": "high" if metric["value"] > threshold * 1.5 else "medium"
        }
        
        self.alerts.append(alert)
        self.logger.warning(f"Performance alert: {alert}") 

class AutoGenPerformanceMonitor:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.start_times: Dict[str, datetime] = {}
        
    async def start_monitoring(self, session_id: str):
        self.start_times[session_id] = datetime.now()
        
    async def record_metric(self, session_id: str, metric_name: str, value: float):
        self.metrics[f"{session_id}_{metric_name}"].append(value)
        
    async def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.start_times:
            return {}
            
        duration = (datetime.now() - self.start_times[session_id]).total_seconds()
        
        session_metrics = {
            "duration": duration,
            "response_times": self.metrics.get(f"{session_id}_response_time", []),
            "token_usage": self.metrics.get(f"{session_id}_token_usage", []),
            "error_rate": len(self.metrics.get(f"{session_id}_errors", [])) / max(1, len(self.metrics.get(f"{session_id}_total_requests", [])))
        }
        
        return session_metrics