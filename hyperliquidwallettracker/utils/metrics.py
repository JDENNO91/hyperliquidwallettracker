"""
Metrics collection and monitoring for HyperLiquidWalletTracker.

This module provides comprehensive metrics collection using Prometheus
for monitoring system health, performance, and business metrics.
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry


@dataclass
class SystemMetrics:
    """System-level metrics."""
    uptime_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    active_connections: int = 0
    total_events_processed: int = 0
    events_per_second: float = 0.0


@dataclass
class BusinessMetrics:
    """Business-level metrics."""
    total_wallets_monitored: int = 0
    whale_events_count: int = 0
    large_events_count: int = 0
    medium_events_count: int = 0
    notable_events_count: int = 0
    notifications_sent: int = 0
    notification_failures: int = 0


class MetricsCollector:
    """
    Comprehensive metrics collector for HyperLiquidWalletTracker.
    
    Collects system metrics, business metrics, and performance metrics
    using Prometheus for monitoring and alerting.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics collector.
        
        Args:
            registry: Optional Prometheus registry to use
        """
        self.registry = registry or CollectorRegistry()
        self.start_time = time.time()
        
        # System metrics
        self.system_metrics = SystemMetrics()
        self.business_metrics = BusinessMetrics()
        
        # Prometheus metrics
        self._setup_prometheus_metrics()
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics."""
        # System metrics
        self.uptime_gauge = Gauge(
            'hyperliquidwallettracker_uptime_seconds',
            'System uptime in seconds',
            registry=self.registry
        )
        
        self.memory_usage_gauge = Gauge(
            'hyperliquidwallettracker_memory_usage_mb',
            'Memory usage in MB',
            registry=self.registry
        )
        
        self.cpu_usage_gauge = Gauge(
            'hyperliquidwallettracker_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.active_connections_gauge = Gauge(
            'hyperliquidwallettracker_active_connections',
            'Number of active connections',
            registry=self.registry
        )
        
        # Event metrics
        self.events_processed_counter = Counter(
            'hyperliquidwallettracker_events_processed_total',
            'Total number of events processed',
            ['event_type', 'wallet', 'status'],
            registry=self.registry
        )
        
        self.events_processing_duration = Histogram(
            'hyperliquidwallettracker_event_processing_duration_seconds',
            'Time spent processing events',
            ['event_type'],
            registry=self.registry
        )
        
        # Business metrics
        self.wallets_monitored_gauge = Gauge(
            'hyperliquidwallettracker_wallets_monitored',
            'Number of wallets being monitored',
            registry=self.registry
        )
        
        self.position_size_counter = Counter(
            'hyperliquidwallettracker_position_events_total',
            'Position events by size classification',
            ['size_class', 'coin'],
            registry=self.registry
        )
        
        # Notification metrics
        self.notifications_sent_counter = Counter(
            'hyperliquidwallettracker_notifications_sent_total',
            'Total notifications sent',
            ['channel', 'status'],
            registry=self.registry
        )
        
        self.notification_duration = Histogram(
            'hyperliquidwallettracker_notification_duration_seconds',
            'Time spent sending notifications',
            ['channel'],
            registry=self.registry
        )
        
        # WebSocket metrics
        self.websocket_reconnects_counter = Counter(
            'hyperliquidwallettracker_websocket_reconnects_total',
            'Total WebSocket reconnections',
            registry=self.registry
        )
        
        self.websocket_health_gauge = Gauge(
            'hyperliquidwallettracker_websocket_healthy',
            'WebSocket health status (1=healthy, 0=unhealthy)',
            registry=self.registry
        )
        
        # Application info
        self.app_info = Info(
            'hyperliquidwallettracker_info',
            'Application information',
            registry=self.registry
        )
        self.app_info.info({
            'version': '2.0.0',
            'name': 'HyperLiquidWalletTracker',
            'description': 'Advanced Hyperliquid wallet monitoring system'
        })
    
    def update_system_metrics(self, **kwargs):
        """Update system-level metrics."""
        for key, value in kwargs.items():
            if hasattr(self.system_metrics, key):
                setattr(self.system_metrics, key, value)
        
        # Update Prometheus gauges
        self.uptime_gauge.set(self.system_metrics.uptime_seconds)
        self.memory_usage_gauge.set(self.system_metrics.memory_usage_mb)
        self.cpu_usage_gauge.set(self.system_metrics.cpu_usage_percent)
        self.active_connections_gauge.set(self.system_metrics.active_connections)
    
    def update_business_metrics(self, **kwargs):
        """Update business-level metrics."""
        for key, value in kwargs.items():
            if hasattr(self.business_metrics, key):
                setattr(self.business_metrics, key, value)
        
        # Update Prometheus gauges
        self.wallets_monitored_gauge.set(self.business_metrics.total_wallets_monitored)
    
    def record_event_processed(
        self, 
        event_type: str, 
        wallet: str, 
        status: str = "success",
        duration: Optional[float] = None
    ):
        """
        Record that an event was processed.
        
        Args:
            event_type: Type of event processed
            wallet: Wallet address
            status: Processing status (success, error, filtered)
            duration: Processing duration in seconds
        """
        self.events_processed_counter.labels(
            event_type=event_type,
            wallet=wallet[:8] + "...",
            status=status
        ).inc()
        
        if duration is not None:
            self.events_processing_duration.labels(
                event_type=event_type
            ).observe(duration)
    
    def record_position_event(self, size_class: str, coin: str):
        """
        Record a position event.
        
        Args:
            size_class: Position size classification (WHALE, LARGE, MEDIUM, NOTABLE)
            coin: Cryptocurrency symbol
        """
        self.position_size_counter.labels(
            size_class=size_class,
            coin=coin
        ).inc()
    
    def record_notification_sent(
        self, 
        channel: str, 
        status: str = "success",
        duration: Optional[float] = None
    ):
        """
        Record that a notification was sent.
        
        Args:
            channel: Notification channel (discord, telegram, email, webhook)
            status: Delivery status (success, error, rate_limited)
            duration: Delivery duration in seconds
        """
        self.notifications_sent_counter.labels(
            channel=channel,
            status=status
        ).inc()
        
        if duration is not None:
            self.notification_duration.labels(
                channel=channel
            ).observe(duration)
    
    def record_websocket_reconnect(self):
        """Record a WebSocket reconnection."""
        self.websocket_reconnects_counter.inc()
    
    def set_websocket_health(self, healthy: bool):
        """
        Set WebSocket health status.
        
        Args:
            healthy: True if WebSocket is healthy, False otherwise
        """
        self.websocket_health_gauge.set(1 if healthy else 0)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current metrics.
        
        Returns:
            Dictionary containing current metrics
        """
        current_time = time.time()
        uptime = current_time - self.start_time
        
        return {
            "system": {
                "uptime_seconds": uptime,
                "uptime_human": self._format_duration(uptime),
                "memory_usage_mb": self.system_metrics.memory_usage_mb,
                "cpu_usage_percent": self.system_metrics.cpu_usage_percent,
                "active_connections": self.system_metrics.active_connections,
                "total_events_processed": self.system_metrics.total_events_processed,
                "events_per_second": self.system_metrics.events_per_second,
            },
            "business": {
                "wallets_monitored": self.business_metrics.total_wallets_monitored,
                "whale_events": self.business_metrics.whale_events_count,
                "large_events": self.business_metrics.large_events_count,
                "medium_events": self.business_metrics.medium_events_count,
                "notable_events": self.business_metrics.notable_events_count,
                "notifications_sent": self.business_metrics.notifications_sent,
                "notification_failures": self.business_metrics.notification_failures,
            }
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"
    
    def export_metrics(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        from prometheus_client import generate_latest
        return generate_latest(self.registry).decode('utf-8')


# Global metrics collector instance
metrics_collector = MetricsCollector()
