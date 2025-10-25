"""
Alert engine for HyperLiquidWalletTracker.

This module provides the core alert processing engine that evaluates
events against rules and triggers notifications.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone

from .rules import RulesEngine, AlertRule
from .classifier import PositionClassifier, PositionSize
from .formatter import NotificationFormatter, NotificationContext
from ..utils.logging import get_logger
from ..utils.metrics import metrics_collector

logger = get_logger(__name__)


class AlertEngine:
    """
    Core alert engine for processing events and triggering notifications.
    
    Features:
    - Event processing and classification
    - Rule evaluation and alert triggering
    - Notification formatting and dispatching
    - Metrics collection and monitoring
    - Event deduplication and aggregation
    """
    
    def __init__(
        self,
        rules_engine: Optional[RulesEngine] = None,
        position_classifier: Optional[PositionClassifier] = None,
        notification_formatter: Optional[NotificationFormatter] = None
    ):
        """
        Initialize alert engine.
        
        Args:
            rules_engine: Rules engine for evaluating events
            position_classifier: Position classifier for size analysis
            notification_formatter: Formatter for notification content
        """
        self.rules_engine = rules_engine or RulesEngine()
        self.position_classifier = position_classifier
        self.notification_formatter = notification_formatter or NotificationFormatter()
        self.notification_handler: Optional[Callable] = None
        
        # Event processing stats
        self.stats = {
            "events_processed": 0,
            "alerts_triggered": 0,
            "notifications_sent": 0,
            "errors": 0,
            "start_time": datetime.now(timezone.utc)
        }
        
        # Event deduplication
        self.recent_events: Dict[str, datetime] = {}
        self.dedup_window_seconds = 30
    
    def set_notification_handler(self, handler: Callable):
        """
        Set the notification handler function.
        
        Args:
            handler: Function to call when notifications should be sent
        """
        self.notification_handler = handler
        logger.info("Notification handler set")
    
    async def process_event(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process an event and generate notifications.
        
        Args:
            event: Event data to process
            
        Returns:
            List of generated notifications
        """
        try:
            self.stats["events_processed"] += 1
            
            # Check for event deduplication
            if self._is_duplicate_event(event):
                logger.debug("Skipping duplicate event")
                return []
            
            # Classify position if classifier is available
            position_analysis = None
            if self.position_classifier:
                position_analysis = self.position_classifier.analyze_position(event)
                if position_analysis:
                    # Track classification
                    self.position_classifier.track_classification(
                        event.get("wallet", "unknown"),
                        position_analysis.size_class
                    )
            
            # Evaluate rules
            triggered_rules = self.rules_engine.evaluate_event(event)
            
            if not triggered_rules:
                logger.debug("No rules triggered for event")
                return []
            
            # Generate notifications
            notifications = []
            for rule in triggered_rules:
                notification = await self._create_notification(event, rule, position_analysis)
                if notification:
                    notifications.append(notification)
            
            # Update stats
            self.stats["alerts_triggered"] += len(triggered_rules)
            self.stats["notifications_sent"] += len(notifications)
            
            # Record metrics
            metrics_collector.record_event_processed(
                event_type=event.get("type", "unknown"),
                wallet=event.get("wallet", "unknown"),
                status="success"
            )
            
            if position_analysis:
                metrics_collector.record_position_event(
                    size_class=position_analysis.size_class.value,
                    coin=event.get("coin", "unknown")
                )
            
            logger.info(f"Processed event: {len(triggered_rules)} rules triggered, {len(notifications)} notifications generated")
            
            return notifications
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error processing event: {e}")
            
            # Record error metrics
            metrics_collector.record_event_processed(
                event_type=event.get("type", "unknown"),
                wallet=event.get("wallet", "unknown"),
                status="error"
            )
            
            return []
    
    def _is_duplicate_event(self, event: Dict[str, Any]) -> bool:
        """Check if event is a duplicate within the deduplication window."""
        # Create event fingerprint
        fingerprint = self._create_event_fingerprint(event)
        
        now = datetime.now(timezone.utc)
        
        # Check if we've seen this event recently
        if fingerprint in self.recent_events:
            last_seen = self.recent_events[fingerprint]
            if (now - last_seen).total_seconds() < self.dedup_window_seconds:
                return True
        
        # Update event tracking
        self.recent_events[fingerprint] = now
        
        # Clean up old events
        cutoff = now.timestamp() - self.dedup_window_seconds * 2
        self.recent_events = {
            fp: timestamp for fp, timestamp in self.recent_events.items()
            if timestamp.timestamp() > cutoff
        }
        
        return False
    
    def _create_event_fingerprint(self, event: Dict[str, Any]) -> str:
        """Create a fingerprint for event deduplication."""
        # Use key fields to create fingerprint
        key_fields = [
            event.get("type"),
            event.get("wallet"),
            event.get("coin"),
            event.get("side"),
            str(event.get("usd_value", "")),
            str(event.get("size", "")),
            str(event.get("price", ""))
        ]
        
        return "|".join(str(field) for field in key_fields if field is not None)
    
    async def _create_notification(
        self, 
        event: Dict[str, Any], 
        rule: AlertRule,
        position_analysis: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a notification for a triggered rule."""
        try:
            # Create notification context
            context = NotificationContext(
                wallet=event.get("wallet", "unknown"),
                event_type=event.get("type", "unknown"),
                position_size=position_analysis.size_class if position_analysis else None,
                usd_value=position_analysis.usd_value if position_analysis else None,
                coin=event.get("coin"),
                side=event.get("side"),
                timestamp=datetime.now(timezone.utc),
                additional_data=event
            )
            
            # Create notification payload
            notification = {
                "rule_name": rule.name,
                "rule_severity": rule.severity.value,
                "context": context,
                "event": event,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Add formatted content for different channels
            notification["formatted"] = {
                "discord": self.notification_formatter.format_discord_notification(context, event),
                "telegram": self.notification_formatter.format_telegram_notification(context, event),
                "email": self.notification_formatter.format_email_notification(context, event),
                "webhook": self.notification_formatter.format_webhook_notification(context, event)
            }
            
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification for rule '{rule.name}': {e}")
            return None
    
    async def send_notification(self, notification: Dict[str, Any]) -> bool:
        """
        Send a notification using the configured handler.
        
        Args:
            notification: Notification to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.notification_handler:
            logger.warning("No notification handler configured")
            return False
        
        try:
            await self.notification_handler(notification)
            logger.info(f"Notification sent for rule '{notification['rule_name']}'")
            return True
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get alert engine statistics."""
        uptime = datetime.now(timezone.utc) - self.stats["start_time"]
        
        return {
            "engine_stats": {
                "events_processed": self.stats["events_processed"],
                "alerts_triggered": self.stats["alerts_triggered"],
                "notifications_sent": self.stats["notifications_sent"],
                "errors": self.stats["errors"],
                "uptime_seconds": uptime.total_seconds(),
                "events_per_second": self.stats["events_processed"] / max(1, uptime.total_seconds())
            },
            "rules_stats": self.rules_engine.get_rule_stats(),
            "deduplication": {
                "recent_events_count": len(self.recent_events),
                "dedup_window_seconds": self.dedup_window_seconds
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the alert engine."""
        error_rate = 0.0
        if self.stats["events_processed"] > 0:
            error_rate = self.stats["errors"] / self.stats["events_processed"]
        
        return {
            "status": "healthy" if error_rate < 0.1 else "degraded",
            "error_rate": error_rate,
            "events_processed": self.stats["events_processed"],
            "alerts_triggered": self.stats["alerts_triggered"],
            "notification_handler_configured": self.notification_handler is not None,
            "rules_count": len(self.rules_engine.rules),
            "enabled_rules_count": len([r for r in self.rules_engine.rules if r.enabled])
        }
    
    def add_rule(self, rule: AlertRule):
        """Add a new rule to the engine."""
        self.rules_engine.add_rule(rule)
        logger.info(f"Added rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove a rule from the engine."""
        self.rules_engine.remove_rule(rule_name)
        logger.info(f"Removed rule: {rule_name}")
    
    def enable_rule(self, rule_name: str):
        """Enable a rule."""
        self.rules_engine.enable_rule(rule_name)
        logger.info(f"Enabled rule: {rule_name}")
    
    def disable_rule(self, rule_name: str):
        """Disable a rule."""
        self.rules_engine.disable_rule(rule_name)
        logger.info(f"Disabled rule: {rule_name}")
    
    def reset_stats(self):
        """Reset engine statistics."""
        self.stats = {
            "events_processed": 0,
            "alerts_triggered": 0,
            "notifications_sent": 0,
            "errors": 0,
            "start_time": datetime.now(timezone.utc)
        }
        logger.info("Alert engine stats reset")
