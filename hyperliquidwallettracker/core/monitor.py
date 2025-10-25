"""
Main HyperLiquidWalletTracker monitor class.

This module provides the primary interface for the HyperLiquidWalletTracker monitoring
system with comprehensive event processing, alerting, and notification capabilities.
"""

import asyncio
import signal
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from .config import HyperLiquidConfig
from .websocket_client import WebSocketClient
from ..alerts.engine import AlertEngine
from ..notifications.dispatcher import NotificationDispatcher
from ..utils.logging import get_logger, setup_logging, LoggerMixin
from ..utils.metrics import metrics_collector

logger = get_logger(__name__)


class HyperLiquidWalletTracker(LoggerMixin):
    """
    Main HyperLiquidWalletTracker monitoring system.
    
    This is the primary interface for the HyperLiquidWalletTracker monitoring system,
    providing real-time Hyperliquid wallet monitoring with intelligent alerting
    and multi-channel notifications.
    
    Features:
    - Real-time WebSocket monitoring
    - Intelligent event processing and classification
    - Multi-channel notification system
    - Comprehensive metrics and monitoring
    - Graceful shutdown handling
    - Configuration validation
    """
    
    def __init__(self, config: Optional[HyperLiquidConfig] = None):
        """
        Initialize HyperLiquidWalletTracker monitor.
        
        Args:
            config: Optional configuration (uses default if not provided)
        """
        self.config = config or HyperLiquidConfig()
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # Initialize components
        self.websocket_client: Optional[WebSocketClient] = None
        self.alert_engine: Optional[AlertEngine] = None
        self.notification_dispatcher: Optional[NotificationDispatcher] = None
        
        # Setup logging
        setup_logging(
            level=self.config.monitoring.log_level,
            format_type="json" if self.config.monitoring.enable_metrics else "console"
        )
        
        # Validate configuration
        self._validate_configuration()
    
    def _validate_configuration(self):
        """Validate configuration and report any issues."""
        issues = self.config.validate_configuration()
        
        if issues:
            self.logger.warning("Configuration issues detected:")
            for issue in issues:
                self.logger.warning(f"  - {issue}")
        else:
            self.logger.info("Configuration validation passed")
    
    async def start(self):
        """
        Start the CryptoPulse monitoring system.
        
        This method initializes all components and begins monitoring.
        """
        if self.is_running:
            self.logger.warning("Monitor is already running")
            return
        
        try:
            self.logger.info("Starting HyperLiquidWalletTracker monitoring system...")
            
            # Initialize notification dispatcher
            self.notification_dispatcher = NotificationDispatcher(self.config)
            await self.notification_dispatcher.start()
            
            # Initialize alert engine
            self.alert_engine = AlertEngine(
                config=self.config,
                notification_dispatcher=self.notification_dispatcher
            )
            await self.alert_engine.start()
            
            # Initialize WebSocket client
            self.websocket_client = WebSocketClient(
                config=self.config,
                event_handler=self._handle_event
            )
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Start monitoring
            self.is_running = True
            self.logger.info("HyperLiquidWalletTracker monitoring system started successfully")
            
            # Start WebSocket client
            await self.websocket_client.run()
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring system: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the CryptoPulse monitoring system gracefully."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping HyperLiquidWalletTracker monitoring system...")
        self.is_running = False
        
        # Stop components in reverse order
        if self.websocket_client:
            await self.websocket_client.shutdown()
        
        if self.alert_engine:
            await self.alert_engine.stop()
        
        if self.notification_dispatcher:
            await self.notification_dispatcher.stop()
        
        # Set shutdown event
        self.shutdown_event.set()
        
        self.logger.info("HyperLiquidWalletTracker monitoring system stopped")
    
    async def _handle_event(self, event: Dict[str, Any]):
        """
        Handle incoming events from WebSocket client.
        
        Args:
            event: Event data to process
        """
        try:
            # Update metrics
            metrics_collector.update_system_metrics(
                total_events_processed=metrics_collector.system_metrics.total_events_processed + 1
            )
            
            # Process through alert engine
            if self.alert_engine:
                await self.alert_engine.process_event(event)
            
            self.logger.debug(f"Processed event: {event.get('type', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Error handling event: {e}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current system status.
        
        Returns:
            Dictionary containing system status information
        """
        status = {
            "is_running": self.is_running,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": {
                "watched_wallets": len(self.config.watched_wallets),
                "enabled_channels": self.config.get_enabled_channels(),
                "log_level": self.config.monitoring.log_level
            }
        }
        
        # Add component status
        if self.websocket_client:
            status["websocket"] = {
                "connected": self.websocket_client.stats.connected,
                "total_messages": self.websocket_client.stats.total_messages,
                "successful_parses": self.websocket_client.stats.successful_parses,
                "reconnect_count": self.websocket_client.stats.reconnect_count
            }
        
        if self.alert_engine:
            status["alert_engine"] = self.alert_engine.get_stats()
        
        if self.notification_dispatcher:
            status["notification_dispatcher"] = self.notification_dispatcher.get_stats()
            status["notification_channels"] = self.notification_dispatcher.get_channel_stats()
        
        # Add metrics
        status["metrics"] = metrics_collector.get_metrics_summary()
        
        return status
    
    async def get_health(self) -> Dict[str, Any]:
        """
        Get system health status.
        
        Returns:
            Dictionary containing health information
        """
        health = {
            "status": "healthy" if self.is_running else "stopped",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {}
        }
        
        # Check WebSocket health
        if self.websocket_client:
            websocket_healthy = (
                self.websocket_client.stats.connected and
                self.websocket_client.stats.consecutive_failures < 5
            )
            health["components"]["websocket"] = {
                "status": "healthy" if websocket_healthy else "unhealthy",
                "connected": self.websocket_client.stats.connected,
                "consecutive_failures": self.websocket_client.stats.consecutive_failures
            }
        else:
            health["components"]["websocket"] = {"status": "not_initialized"}
        
        # Check alert engine health
        if self.alert_engine:
            alert_engine_healthy = self.alert_engine.is_running
            health["components"]["alert_engine"] = {
                "status": "healthy" if alert_engine_healthy else "unhealthy",
                "is_running": alert_engine_healthy
            }
        else:
            health["components"]["alert_engine"] = {"status": "not_initialized"}
        
        # Check notification dispatcher health
        if self.notification_dispatcher:
            dispatcher_healthy = self.notification_dispatcher.is_running
            health["components"]["notification_dispatcher"] = {
                "status": "healthy" if dispatcher_healthy else "unhealthy",
                "is_running": dispatcher_healthy
            }
        else:
            health["components"]["notification_dispatcher"] = {"status": "not_initialized"}
        
        # Overall health
        all_healthy = all(
            comp.get("status") == "healthy" 
            for comp in health["components"].values()
        )
        health["overall_status"] = "healthy" if all_healthy else "degraded"
        
        return health
    
    async def run_forever(self):
        """
        Run the monitoring system indefinitely.
        
        This method starts the system and runs until stopped.
        """
        try:
            await self.start()
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}")
        finally:
            await self.stop()
    
    def get_configuration(self) -> Dict[str, Any]:
        """
        Get current configuration.
        
        Returns:
            Dictionary containing configuration information
        """
        return {
            "watched_wallets": self.config.watched_wallets,
            "websocket_url": self.config.websocket_url,
            "thresholds": {
                "notable": self.config.thresholds.notable_threshold,
                "medium": self.config.thresholds.medium_threshold,
                "large": self.config.thresholds.large_threshold,
                "whale": self.config.thresholds.whale_threshold
            },
            "channels": {
                "discord": {
                    "enabled": self.config.discord.enabled,
                    "configured": bool(self.config.discord.webhook_url)
                },
                "telegram": {
                    "enabled": self.config.telegram.enabled,
                    "configured": bool(self.config.telegram.bot_token and self.config.telegram.chat_id)
                },
                "email": {
                    "enabled": self.config.email.enabled,
                    "configured": bool(self.config.email.username and self.config.email.to_addrs)
                },
                "webhook": {
                    "enabled": self.config.webhook.enabled,
                    "configured": bool(self.config.webhook.url)
                }
            },
            "monitoring": {
                "enable_metrics": self.config.monitoring.enable_metrics,
                "log_level": self.config.monitoring.log_level,
                "health_check_interval": self.config.monitoring.health_check_interval
            }
        }
