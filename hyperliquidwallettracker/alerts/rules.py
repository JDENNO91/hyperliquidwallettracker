"""
Alert rules engine for HyperLiquidWalletTracker.

This module defines alert rules, conditions, and the rules engine for
processing events and determining when to trigger alerts.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

from ..utils.logging import get_logger

logger = get_logger(__name__)


class AlertCondition(Enum):
    """Alert condition types."""
    POSITION_SIZE = "position_size"
    VOLUME_THRESHOLD = "volume_threshold"
    PRICE_CHANGE = "price_change"
    FREQUENCY = "frequency"
    CUSTOM = "custom"


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    condition: AlertCondition
    severity: AlertSeverity
    enabled: bool = True
    description: str = ""
    threshold: Optional[float] = None
    time_window: Optional[int] = None  # seconds
    custom_condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Default alert rules
DEFAULT_RULES = [
    AlertRule(
        name="whale_position",
        condition=AlertCondition.POSITION_SIZE,
        severity=AlertSeverity.CRITICAL,
        description="Detect whale-sized positions (≥$1M USD)",
        threshold=1000000.0,
        metadata={"size_class": "WHALE"}
    ),
    AlertRule(
        name="large_position", 
        condition=AlertCondition.POSITION_SIZE,
        severity=AlertSeverity.HIGH,
        description="Detect large positions (≥$100K USD)",
        threshold=100000.0,
        metadata={"size_class": "LARGE"}
    ),
    AlertRule(
        name="medium_position",
        condition=AlertCondition.POSITION_SIZE, 
        severity=AlertSeverity.MEDIUM,
        description="Detect medium positions (≥$10K USD)",
        threshold=10000.0,
        metadata={"size_class": "MEDIUM"}
    ),
    AlertRule(
        name="notable_position",
        condition=AlertCondition.POSITION_SIZE,
        severity=AlertSeverity.LOW,
        description="Detect notable positions (≥$1K USD)",
        threshold=1000.0,
        metadata={"size_class": "NOTABLE"}
    ),
    AlertRule(
        name="high_frequency_trading",
        condition=AlertCondition.FREQUENCY,
        severity=AlertSeverity.MEDIUM,
        description="Detect high-frequency trading activity",
        threshold=10,  # events per minute
        time_window=60,
        metadata={"activity_type": "high_frequency"}
    ),
    AlertRule(
        name="unusual_volume",
        condition=AlertCondition.VOLUME_THRESHOLD,
        severity=AlertSeverity.HIGH,
        description="Detect unusual trading volume",
        threshold=50000.0,  # USD
        time_window=300,  # 5 minutes
        metadata={"volume_type": "unusual"}
    )
]


class RulesEngine:
    """
    Rules engine for processing events and triggering alerts.
    
    Features:
    - Rule evaluation with multiple conditions
    - Time-based rule processing
    - Custom condition support
    - Rule statistics and monitoring
    """
    
    def __init__(self, rules: List[AlertRule] = None):
        """
        Initialize rules engine.
        
        Args:
            rules: List of alert rules (defaults to DEFAULT_RULES)
        """
        self.rules = rules or DEFAULT_RULES
        self.rule_stats: Dict[str, Dict[str, Any]] = {}
        self.event_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # Initialize rule statistics
        for rule in self.rules:
            self.rule_stats[rule.name] = {
                "triggered_count": 0,
                "last_triggered": None,
                "total_events": 0,
                "success_rate": 0.0
            }
    
    def evaluate_event(self, event: Dict[str, Any]) -> List[AlertRule]:
        """
        Evaluate an event against all rules.
        
        Args:
            event: Event data to evaluate
            
        Returns:
            List of triggered rules
        """
        triggered_rules = []
        
        # Add event to history
        self._add_to_history(event)
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                if self._evaluate_rule(rule, event):
                    triggered_rules.append(rule)
                    self._update_rule_stats(rule, True)
                    logger.info(f"Rule '{rule.name}' triggered for event")
                else:
                    self._update_rule_stats(rule, False)
                    
            except Exception as e:
                logger.error(f"Error evaluating rule '{rule.name}': {e}")
                self._update_rule_stats(rule, False, error=True)
        
        return triggered_rules
    
    def _evaluate_rule(self, rule: AlertRule, event: Dict[str, Any]) -> bool:
        """Evaluate a single rule against an event."""
        if rule.condition == AlertCondition.POSITION_SIZE:
            return self._evaluate_position_size(rule, event)
        
        elif rule.condition == AlertCondition.VOLUME_THRESHOLD:
            return self._evaluate_volume_threshold(rule, event)
        
        elif rule.condition == AlertCondition.PRICE_CHANGE:
            return self._evaluate_price_change(rule, event)
        
        elif rule.condition == AlertCondition.FREQUENCY:
            return self._evaluate_frequency(rule, event)
        
        elif rule.condition == AlertCondition.CUSTOM:
            return self._evaluate_custom(rule, event)
        
        return False
    
    def _evaluate_position_size(self, rule: AlertRule, event: Dict[str, Any]) -> bool:
        """Evaluate position size condition."""
        if rule.threshold is None:
            return False
        
        # Extract USD value from event
        usd_value = self._extract_usd_value(event)
        if usd_value is None:
            return False
        
        return usd_value >= rule.threshold
    
    def _evaluate_volume_threshold(self, rule: AlertRule, event: Dict[str, Any]) -> bool:
        """Evaluate volume threshold condition."""
        if rule.threshold is None or rule.time_window is None:
            return False
        
        # Get events within time window
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - rule.time_window
        
        recent_events = [
            e for e in self.event_history
            if e.get("timestamp", 0) >= cutoff
        ]
        
        # Calculate total volume
        total_volume = sum(
            self._extract_usd_value(e) or 0
            for e in recent_events
        )
        
        return total_volume >= rule.threshold
    
    def _evaluate_price_change(self, rule: AlertRule, event: Dict[str, Any]) -> bool:
        """Evaluate price change condition."""
        # This would require historical price data
        # For now, return False as we don't have price history
        return False
    
    def _evaluate_frequency(self, rule: AlertRule, event: Dict[str, Any]) -> bool:
        """Evaluate frequency condition."""
        if rule.threshold is None or rule.time_window is None:
            return False
        
        # Get events within time window for same wallet
        wallet = event.get("wallet")
        if not wallet:
            return False
        
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - rule.time_window
        
        recent_events = [
            e for e in self.event_history
            if (e.get("wallet") == wallet and 
                e.get("timestamp", 0) >= cutoff)
        ]
        
        return len(recent_events) >= rule.threshold
    
    def _evaluate_custom(self, rule: AlertRule, event: Dict[str, Any]) -> bool:
        """Evaluate custom condition."""
        if rule.custom_condition is None:
            return False
        
        try:
            return rule.custom_condition(event)
        except Exception as e:
            logger.error(f"Error in custom condition for rule '{rule.name}': {e}")
            return False
    
    def _extract_usd_value(self, event: Dict[str, Any]) -> Optional[float]:
        """Extract USD value from event data."""
        # Try different field names for USD value
        usd_fields = [
            "usd_value", "usdValue", "value_usd", "valueUSD",
            "total_value", "totalValue", "amount_usd", "amountUSD"
        ]
        
        for field in usd_fields:
            if field in event and event[field] is not None:
                try:
                    return float(event[field])
                except (ValueError, TypeError):
                    continue
        
        # Try to calculate from price and size
        price = event.get("price") or event.get("limitPx") or event.get("limit_px")
        size = event.get("size") or event.get("sz") or event.get("quantity")
        
        if price is not None and size is not None:
            try:
                return float(price) * float(size)
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _add_to_history(self, event: Dict[str, Any]):
        """Add event to history for time-based rules."""
        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = datetime.now(timezone.utc).timestamp()
        
        self.event_history.append(event)
        
        # Keep history size manageable
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size:]
    
    def _update_rule_stats(self, rule: AlertRule, triggered: bool, error: bool = False):
        """Update rule statistics."""
        stats = self.rule_stats[rule.name]
        stats["total_events"] += 1
        
        if triggered:
            stats["triggered_count"] += 1
            stats["last_triggered"] = datetime.now(timezone.utc)
        
        # Calculate success rate
        if stats["total_events"] > 0:
            stats["success_rate"] = stats["triggered_count"] / stats["total_events"]
    
    def get_rule_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all rules."""
        return self.rule_stats.copy()
    
    def get_triggered_rules(self, time_window: int = 3600) -> List[str]:
        """Get rules that have been triggered within the time window."""
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - time_window
        
        triggered = []
        for rule_name, stats in self.rule_stats.items():
            if (stats["last_triggered"] and 
                stats["last_triggered"].timestamp() >= cutoff):
                triggered.append(rule_name)
        
        return triggered
    
    def add_rule(self, rule: AlertRule):
        """Add a new rule to the engine."""
        self.rules.append(rule)
        self.rule_stats[rule.name] = {
            "triggered_count": 0,
            "last_triggered": None,
            "total_events": 0,
            "success_rate": 0.0
        }
        logger.info(f"Added rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove a rule from the engine."""
        self.rules = [r for r in self.rules if r.name != rule_name]
        if rule_name in self.rule_stats:
            del self.rule_stats[rule_name]
        logger.info(f"Removed rule: {rule_name}")
    
    def enable_rule(self, rule_name: str):
        """Enable a rule."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                logger.info(f"Enabled rule: {rule_name}")
                break
    
    def disable_rule(self, rule_name: str):
        """Disable a rule."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                logger.info(f"Disabled rule: {rule_name}")
                break
